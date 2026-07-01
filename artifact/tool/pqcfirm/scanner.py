import os
from tree_sitter import Language, Parser, Node
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp

from .rules import (
    Finding,
    check_r01_hardcoded_key_size,
    check_r02_rigid_algo_selection,
    check_r03_stack_crypto_buffer,
    check_r04_unchecked_crypto_return,
    check_r05_algorithm_specific_api,
    check_r06_unsafe_malloc_keysize,
    check_r07_contract_violation
)

class Scanner:
    def __init__(self, rules: list[str] = None):
        self.lang_c = Language(tsc.language())
        self.lang_cpp = Language(tscpp.language())
        self.parser_c = Parser(self.lang_c)
        self.parser_cpp = Parser(self.lang_cpp)
        
        # Enabled rules
        self.enabled_rules = set(rules) if rules else {"R01", "R02", "R03", "R04", "R05", "R06", "R07"}

    def scan_file(self, file_path: str) -> list[Finding]:
        """Scan a single C/C++ file and return findings."""
        if not os.path.exists(file_path):
            return []
            
        _, ext = os.path.splitext(file_path.lower())
        is_cpp = ext in ('.cpp', '.cc', '.cxx', '.hpp', '.h++', '.hh', '.hxx')
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except Exception:
            return []
            
        parser = self.parser_cpp if is_cpp else self.parser_c
        tree = parser.parse(content)
        
        findings = []
        
        def walk(node: Node, in_function: bool = False):
            # Run enabled rules on this node
            if "R01" in self.enabled_rules:
                findings.extend(check_r01_hardcoded_key_size(node, file_path))
            if "R02" in self.enabled_rules:
                findings.extend(check_r02_rigid_algo_selection(node, file_path))
            if "R03" in self.enabled_rules:
                findings.extend(check_r03_stack_crypto_buffer(node, file_path, in_function))
            if "R04" in self.enabled_rules:
                findings.extend(check_r04_unchecked_crypto_return(node, file_path))
            if "R05" in self.enabled_rules:
                findings.extend(check_r05_algorithm_specific_api(node, file_path))
            if "R06" in self.enabled_rules:
                findings.extend(check_r06_unsafe_malloc_keysize(node, file_path))
            if "R07" in self.enabled_rules:
                findings.extend(check_r07_contract_violation(node, file_path))
                
            # Update context
            new_in_function = in_function or (node.type in ('function_definition', 'generator_definition'))
            
            # Recurse to children
            for child in node.children:
                walk(child, new_in_function)
                
        walk(tree.root_node)
        return findings

    def scan_directory(self, dir_path: str, recursive: bool = True) -> list[Finding]:
        """Scan all C/C++ files in a directory."""
        findings = []
        if not os.path.exists(dir_path):
            return []
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                _, ext = os.path.splitext(file.lower())
                if ext in ('.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.hh', '.hxx'):
                    file_path = os.path.join(root, file)
                    findings.extend(self.scan_file(file_path))
            if not recursive:
                break
                
        return findings
