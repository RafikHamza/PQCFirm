import re
from tree_sitter import Node

class Finding:
    def __init__(self, file_path: str, line: int, col: int, rule_id: str, severity: str, message: str, suggestion: str):
        self.file_path = file_path
        self.line = line  # 1-indexed for user display
        self.col = col    # 0-indexed
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "line": self.line,
            "col": self.col,
            "rule": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion
        }

# Crypto-related keywords
CRYPTO_KEYWORDS_RE = re.compile(
    r'(key|secret|pk|sk|pub|priv|ciphertext|ct|signature|sig|seed|salt|plain|pt|digest|hash|mac|tag|auth|cert|certificate|handshake|kex|kem)',
    re.IGNORECASE
)

# Byte types
BYTE_TYPES = {"uint8_t", "char", "unsigned char", "uint8", "BYTE", "unsigned char", "u8"}

# R01 is narrower than the general crypto-keyword set: it focuses on
# externally sized key/certificate/handshake/signature buffers, not internal
# PQC parameter constants or symmetric/hash working buffers.
R01_BUFFER_RE = re.compile(
    r'(key|secret|pk|sk|pub|priv|ciphertext|ct|signature|sig|psk|cert|certificate|handshake|kex|kem)',
    re.IGNORECASE
)
R01_EXCLUDED_IDENTIFIER_RE = re.compile(
    r'(AES|HMAC|CMAC|GCM|CCM|CHACHA|POLY1305|HASH|DIGEST|SEED|SALT|CTR|PLAIN|DECRYPTED|ALG_|MLKEM_[KN]|MLKEM_ETA|MLKEM_D[UV]|MLKEM_POLY|SEEDBYTES|SYMBYTES|POLYBYTES)',
    re.IGNORECASE
)

# Classical vs PQC identifiers
CLASSICAL_RE = re.compile(r'(RSA|ECDSA|ECDH|ECC|DSA|DH|AES|DES|3DES|RC4|MD5|SHA1|P256|P384|P521|X25519|X448)', re.IGNORECASE)
PQC_RE = re.compile(r'(KYBER|DILITHIUM|ML_KEM|ML_DSA|MLKEM|MLDSA|OQS|PQC|SPHINCS|FALCON|BIKE|HQC|MCELIECE)', re.IGNORECASE)

# Algorithm-specific patterns for R05
ALGO_SPECIFIC_RE = re.compile(r'(kyber|dilithium|sphincs|falcon|mceliece|hqc)', re.IGNORECASE)
CRYPTO_OP_RE = re.compile(r'(keypair|keygen|generate|gen_public|encaps|decaps|sign|verify|encrypt|decrypt|import|export|handshake|setkey|set_hs|parse|read|write|compute|derive|crypt|rng|randombytes)', re.IGNORECASE)

def get_node_text(node: Node) -> str:
    return node.text.decode('utf-8', errors='ignore')

def is_status_return_crypto_call(func_name: str) -> bool:
    """Return True for crypto calls whose discarded return value is actionable.

    The rule deliberately avoids lifecycle and byte-shuffling helpers (init/free,
    reset/release, SHA3 absorb/finalize/squeeze, etc.) because many of those APIs
    either return void or do not represent a PQC migration security decision. The
    goal is a high-confidence actionable mode, not sound detection of every
    possible unchecked call.
    """
    if not func_name:
        return False
    lower = func_name.lower()

    lifecycle_terms = (
        "init", "free", "cleanup", "reset", "release", "zeroize",
        "deinit", "destroy", "close", "clear", "wipe"
    )
    utility_terms = (
        "absorb", "finalize", "squeeze", "sha3", "shake", "keccak",
        "memset", "memcpy", "printf", "snprintf", "debug"
    )
    status_terms = (
        "keypair", "keygen", "generate", "gen_public", "encaps", "decaps",
        "sign", "verify", "encrypt", "decrypt", "import", "export",
        "handshake", "setkey", "set_hs", "parse", "read", "write",
        "compute", "derive", "crypt", "rng", "randombytes"
    )

    has_crypto_namespace = (
        func_name.startswith("OQS_") or lower.startswith("mbedtls_") or
        lower.startswith("psa_") or lower.startswith("wc_") or
        lower.startswith("crypto_") or lower.startswith("ml_kem") or
        lower.startswith("mlkem") or lower.startswith("dilithium") or
        lower.startswith("kyber")
    )
    has_status_operation = any(term in lower for term in status_terms)

    # Lifecycle and sponge/hash utility helpers are intentionally not reported
    # unless their name also contains a clear status-returning crypto operation.
    if any(term in lower for term in lifecycle_terms + utility_terms) and not has_status_operation:
        return False

    return has_crypto_namespace and has_status_operation

def check_r01_hardcoded_key_size(node: Node, file_path: str) -> list[Finding]:
    """
    R01: Hardcoded key size constants or array declarations under PQC threshold (< 512 bytes).
    """
    findings = []
    
    # 1. Check macro definitions (#define KEY_SIZE 32)
    if node.type == 'preproc_def':
        identifier = None
        preproc_arg = None
        for child in node.children:
            if child.type == 'identifier':
                identifier = get_node_text(child)
            elif child.type == 'preproc_arg':
                preproc_arg = get_node_text(child).strip()
        
        if identifier and preproc_arg:
            if R01_BUFFER_RE.search(identifier) and not R01_EXCLUDED_IDENTIFIER_RE.search(identifier):
                # Try to parse as integer
                try:
                    val = int(preproc_arg)
                    identifier_lower = identifier.lower()
                    threshold = 4096 if any(t in identifier_lower for t in ('cert', 'certificate', 'handshake')) else 512
                    if 0 < val < threshold:
                        findings.append(Finding(
                             file_path=file_path,
                             line=node.start_point[0] + 1,
                             col=node.start_point[1],
                             rule_id="R01",
                             severity="medium",
                             message=f"Hardcoded key/buffer size macro '{identifier}' value ({val}) is below PQC minimum requirements.",
                             suggestion="Use a parameterized constant or a post-quantum size constant (e.g. ML-KEM key sizes > 800 bytes)."
                        ))
                except ValueError:
                    pass

    # 2. Check array declarations: uint8_t pk[32]
    elif node.type == 'array_declarator':
        # Find declaration parent to check type (if available)
        parent = node.parent
        is_byte_type = False
        while parent and parent.type not in ('declaration', 'parameter_declaration', 'field_declaration'):
            parent = parent.parent
        
        if parent:
            type_str = ""
            for child in parent.children:
                if child.type in ('primitive_type', 'type_identifier', 'typedef_type'):
                    type_str = get_node_text(child)
                    break
            if any(t in type_str for t in BYTE_TYPES):
                is_byte_type = True

        # Extract identifier and size
        identifier = None
        size_val = None
        for child in node.children:
            if child.type == 'identifier':
                identifier = get_node_text(child)
            elif child.type == 'number_literal':
                try:
                    size_val = int(get_node_text(child))
                except ValueError:
                    pass
        
        if identifier and size_val is not None:
            if R01_BUFFER_RE.search(identifier) and not R01_EXCLUDED_IDENTIFIER_RE.search(identifier) and (is_byte_type or len(identifier) <= 4):
                identifier_lower = identifier.lower()
                threshold = 4096 if any(t in identifier_lower for t in ('cert', 'certificate', 'handshake')) else 512
                if 0 < size_val < threshold:
                    findings.append(Finding(
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                        col=node.start_point[1],
                        rule_id="R01",
                        severity="high",
                        message=f"Hardcoded key array size ({size_val} bytes) for '{identifier}' is insufficient for PQC.",
                        suggestion="Increase array size to hold PQC public/private keys or signatures, or parameterize it."
                    ))
                    
    return findings


def check_r02_rigid_algo_selection(node: Node, file_path: str) -> list[Finding]:
    """
    R02: Switch/if-else chains checking algorithms without PQC cases.
    """
    findings = []
    
    def collect_identifiers(n: Node) -> list[str]:
        ids = []
        if n.type in ('identifier', 'string_literal', 'comment'):
            ids.append(get_node_text(n))
        for child in n.children:
            ids.extend(collect_identifiers(child))
        return ids

    if node.type == 'switch_statement':
        # Collect all identifiers in the switch block
        ids = collect_identifiers(node)
        has_classical = any(CLASSICAL_RE.search(i) for i in ids)
        has_pqc = any(PQC_RE.search(i) for i in ids)
        
        if has_classical and not has_pqc:
            findings.append(Finding(
                file_path=file_path,
                line=node.start_point[0] + 1,
                col=node.start_point[1],
                rule_id="R02",
                severity="medium",
                message="Algorithm switch statement contains classical crypto but lacks post-quantum cryptography cases.",
                suggestion="Implement crypto agility by adding ML-KEM or ML-DSA cases."
            ))
            
    elif node.type == 'if_statement':
        # Check if this is the start of an if/else-if chain (parent is not an else clause)
        parent = node.parent
        if parent and parent.type == 'else_clause':
            return findings # Will check at the root of the chain
            
        # Collect all identifiers in this if statement and its else-if branches
        ids = []
        curr = node
        while curr and curr.type == 'if_statement':
            # Add identifiers in condition
            cond = None
            for child in curr.children:
                if child.type in ('parenthesized_expression', 'condition_clause'):
                    cond = child
                    break
            if cond:
                ids.extend(collect_identifiers(cond))
            
            # Find next else-if
            next_if = None
            for child in curr.children:
                if child.type == 'else_clause':
                    for sub in child.children:
                        if sub.type == 'if_statement':
                            next_if = sub
                            break
            curr = next_if
            
        has_classical = any(CLASSICAL_RE.search(i) for i in ids)
        has_pqc = any(PQC_RE.search(i) for i in ids)
        
        if has_classical and not has_pqc:
            findings.append(Finding(
                file_path=file_path,
                line=node.start_point[0] + 1,
                col=node.start_point[1],
                rule_id="R02",
                severity="medium",
                message="Algorithm if-else chain contains classical checks but lacks post-quantum cryptography options.",
                suggestion="Refactor to support post-quantum algorithms."
            ))
            
    return findings


def check_r03_stack_crypto_buffer(node: Node, file_path: str, in_function: bool) -> list[Finding]:
    """
    R03: Large stack-allocated crypto buffers (>= 1024 bytes) inside functions.
    """
    findings = []
    if not in_function:
        return findings
        
    if node.type == 'array_declarator':
        # Extract identifier and size/macro
        identifier = None
        size_node = None
        for child in node.children:
            if child.type == 'identifier':
                if identifier is None:
                    identifier = get_node_text(child)
                else:
                    size_node = child
            elif child.type == 'number_literal':
                size_node = child
        
        if identifier and size_node:
            size_text = get_node_text(size_node)
            is_large = False
            
            # Case 1: Large number literal (>= 1024 bytes)
            if size_node.type == 'number_literal':
                try:
                    val = int(size_text)
                    if val >= 1024:
                        is_large = True
                except ValueError:
                    pass
            # Case 2: PQC-specific or crypto-size macro/expression name
            elif size_node.type in ('identifier', 'binary_expression'):
                if PQC_RE.search(size_text) or CRYPTO_KEYWORDS_RE.search(size_text):
                    is_large = True
                    
            if is_large and (CRYPTO_KEYWORDS_RE.search(identifier) or 'buffer' in identifier.lower()):
                findings.append(Finding(
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    col=node.start_point[1],
                    rule_id="R03",
                    severity="high",
                    message=f"Stack-allocated crypto buffer '{identifier}' of large size ({size_text}) detected.",
                    suggestion="PQC keys/buffers are large; allocate on the heap or use caller-provided memory to prevent stack exhaustion."
                ))
                
    return findings


def check_r04_unchecked_crypto_return(node: Node, file_path: str) -> list[Finding]:
    """
    R04: Unchecked cryptographic function return values.
    """
    findings = []
    
    if node.type == 'call_expression':
        # Check if parent is expression_statement (which means return value is discarded)
        if node.parent and node.parent.type == 'expression_statement':
            func_name = ""
            for child in node.children:
                if child.type == 'identifier':
                    func_name = get_node_text(child)
                    break
                    
            if func_name:
                if is_status_return_crypto_call(func_name):
                    # Apply a lightweight triage filter to reduce false positives
                    # (Note: this is a triage filter, not a soundness rule)
                    path_lower = file_path.lower().replace('/', '\\')
                    if any(hint in path_lower for hint in ["\\test\\", "\\tests\\", "\\example\\", "\\examples\\", "\\fuzz\\", "\\benchmark\\", "\\bench\\"]):
                        return findings

                    findings.append(Finding(
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                        col=node.start_point[1],
                        rule_id="R04",
                        severity="high",
                        message=f"Return value of cryptographic function '{func_name}' is unchecked.",
                        suggestion="Check the return value for errors (e.g. decapsulation failure) to prevent security gaps."
                    ))
                    
    return findings


def check_r05_algorithm_specific_api(node: Node, file_path: str) -> list[Finding]:
    """
    R05: Algorithm-specific API usage instead of generic/parameterized API.
    """
    findings = []
    
    if node.type == 'call_expression':
        func_name = ""
        for child in node.children:
            if child.type == 'identifier':
                func_name = get_node_text(child)
                break
                
        if func_name:
            # Check if function name contains algorithm-specific string AND a crypto operation
            if ALGO_SPECIFIC_RE.search(func_name) and CRYPTO_OP_RE.search(func_name):
                findings.append(Finding(
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    col=node.start_point[1],
                    rule_id="R05",
                    severity="low",
                    message=f"Direct call to algorithm-specific API '{func_name}'.",
                    suggestion="Use parameterized generic APIs (e.g., OQS_KEM_decaps or wrapper functions) to maintain crypto-agility."
                ))
                
    return findings


def check_r06_unsafe_malloc_keysize(node: Node, file_path: str) -> list[Finding]:
    """
    R06: Unbounded or unchecked malloc/calloc using key/buffer sizes (leads to integer overflow).
    """
    findings = []
    
    if node.type == 'call_expression':
        func_name = ""
        for child in node.children:
            if child.type == 'identifier':
                func_name = get_node_text(child)
                break
                
        if func_name in ("malloc", "calloc", "realloc", "pvPortMalloc"):
            # Check argument list
            args = []
            for child in node.children:
                if child.type == 'argument_list':
                    # Traverse argument list children to find expressions
                    for arg in child.children:
                        if arg.type not in ('(', ')', ','):
                            args.append(arg)
            
            for arg in args:
                # Check if the argument is a binary expression (+ or *)
                def has_arithmetic_on_sizes(n: Node) -> bool:
                    if n.type == 'binary_expression':
                        op = ""
                        for c in n.children:
                            if c.type in ('+', '*'):
                                op = get_node_text(c)
                        
                        # Find if operands contain key size variables
                        text = get_node_text(n)
                        if op in ('+', '*') and CRYPTO_KEYWORDS_RE.search(text):
                            return True
                            
                    # Check recursively
                    for child in n.children:
                        if has_arithmetic_on_sizes(child):
                            return True
                    return False
                
                if has_arithmetic_on_sizes(arg):
                    findings.append(Finding(
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                        col=node.start_point[1],
                        rule_id="R06",
                        severity="high",
                        message=f"Memory allocation '{func_name}' size calculation uses arithmetic on key/buffer sizes without overflow checks.",
                        suggestion="Validate allocation sizes or check for integer overflow (e.g. key_len + sig_len) before allocating."
                    ))
                    
    return findings


def check_r07_contract_violation(node: Node, file_path: str) -> list[Finding]:
    """
    R07: Cryptographic return value postcondition contract violation.
    Detects if a function captures a cryptographic operation return value in a local variable,
    and returns that variable without any validation check present in the function body.
    """
    findings = []
    
    if node.type == 'function_definition':
        captured_vars = {}  # name -> line
        checked_vars = set()
        returned_vars = []
        
        def is_crypto_func(func_name: str) -> bool:
            return (
                "OQS_" in func_name or
                "mbedtls_" in func_name or
                "wc_" in func_name or
                "crypto_" in func_name or
                CRYPTO_OP_RE.search(func_name) is not None
            )
            
        def walk_ast(n: Node):
            # 1. Capture variables from assignment_expression / init_declarator
            if n.type == 'assignment_expression':
                lhs = None
                rhs = None
                for child in n.children:
                    if child.type == 'identifier':
                        lhs = get_node_text(child)
                    elif child.type == 'call_expression':
                        rhs = child
                if lhs and rhs:
                    func_name = ""
                    for sub in rhs.children:
                        if sub.type == 'identifier':
                            func_name = get_node_text(sub)
                    if func_name and is_crypto_func(func_name):
                        captured_vars[lhs] = n.start_point[0] + 1
                        
            elif n.type == 'init_declarator':
                lhs = None
                rhs = None
                for child in n.children:
                    if child.type == 'identifier':
                        lhs = get_node_text(child)
                    elif child.type == 'call_expression':
                        rhs = child
                if lhs and rhs:
                    func_name = ""
                    for sub in rhs.children:
                        if sub.type == 'identifier':
                            func_name = get_node_text(sub)
                    if func_name and is_crypto_func(func_name):
                        captured_vars[lhs] = n.start_point[0] + 1
                        
            # 2. Check for validation / conditional checks
            elif n.type in ('if_statement', 'switch_statement', 'conditional_expression'):
                cond_nodes = []
                if n.type == 'if_statement':
                    for child in n.children:
                        if child.type in ('parenthesized_expression', 'condition_clause'):
                            cond_nodes.append(child)
                elif n.type == 'switch_statement':
                    for child in n.children:
                        if child.type in ('parenthesized_expression', 'condition_clause'):
                            cond_nodes.append(child)
                elif n.type == 'conditional_expression':
                    if len(n.children) > 0:
                        cond_nodes.append(n.children[0])
                        
                def collect_ids(node_to_check: Node):
                    if node_to_check.type == 'identifier':
                        checked_vars.add(get_node_text(node_to_check))
                    for child in node_to_check.children:
                        collect_ids(child)
                        
                for c in cond_nodes:
                    collect_ids(c)
                    
            elif n.type == 'binary_expression':
                has_comparison = False
                for child in n.children:
                    if child.type in ('==', '!=', '<', '>', '<=', '>=', '&&', '||'):
                        has_comparison = True
                        break
                if has_comparison:
                    def collect_ids(node_to_check: Node):
                        if node_to_check.type == 'identifier':
                            checked_vars.add(get_node_text(node_to_check))
                        for child in node_to_check.children:
                            collect_ids(child)
                    collect_ids(n)
                    
            elif n.type == 'unary_expression':
                has_negation = False
                for child in n.children:
                    if get_node_text(child) == '!':
                        has_negation = True
                        break
                if has_negation:
                    def collect_ids(node_to_check: Node):
                        if node_to_check.type == 'identifier':
                            checked_vars.add(get_node_text(node_to_check))
                        for child in node_to_check.children:
                            collect_ids(child)
                    collect_ids(n)
                    
            # 3. Check for return statement
            elif n.type == 'return_statement':
                def collect_return_ids(ret_node: Node):
                    if ret_node.type == 'identifier':
                        returned_vars.append((get_node_text(ret_node), n.start_point[0] + 1))
                    for child in ret_node.children:
                        collect_return_ids(child)
                collect_return_ids(n)
                
            for child in n.children:
                walk_ast(child)
                
        walk_ast(node)
        
        # Verify if any returned variable was captured but NOT checked
        for ret_var, ret_line in returned_vars:
            if ret_var in captured_vars and ret_var not in checked_vars:
                findings.append(Finding(
                    file_path=file_path,
                    line=captured_vars[ret_var],
                    col=node.start_point[1],
                    rule_id="R07",
                    severity="medium",
                    message=f"Return contract violation: variable '{ret_var}' stores crypto result but is returned without validation.",
                    suggestion="Ensure the return value contract is validated (e.g. checking for non-zero status) before returning."
                ))
                
    return findings

