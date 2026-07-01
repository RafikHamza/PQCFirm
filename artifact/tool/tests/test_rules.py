import os
import tempfile
import unittest
from pqcfirm.scanner import Scanner

class TestPQCFirmRules(unittest.TestCase):
    def setUp(self):
        self.scanner = Scanner()
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            try:
                os.remove(f)
            except Exception:
                pass

    def create_temp_file(self, content: str, suffix: str = ".c") -> str:
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            self.temp_files.append(f.name)
            return f.name

    def test_r01_hardcoded_key_size_macro(self):
        # Positive case (macro size under 512)
        code = """
        #define AES_KEY_SIZE 32
        #define KYBER_768_PK_SIZE 1184
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r01_findings = [f for f in findings if f.rule_id == "R01"]
        self.assertEqual(len(r01_findings), 1)
        self.assertIn("AES_KEY_SIZE", r01_findings[0].message)

    def test_r01_hardcoded_key_size_array(self):
        # Positive case (array size under 512 with key keyword)
        code = """
        void process() {
            uint8_t public_key[32] = {0};
            uint8_t pqc_pk[1184];
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r01_findings = [f for f in findings if f.rule_id == "R01"]
        self.assertEqual(len(r01_findings), 1)
        self.assertIn("public_key", r01_findings[0].message)

    def test_r02_rigid_algo_selection_switch(self):
        # Positive case: switch with classical algorithms but no PQC
        code = """
        void setup_algo(int type) {
            switch(type) {
                case RSA:
                    break;
                case ECDSA:
                    break;
            }
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r02_findings = [f for f in findings if f.rule_id == "R02"]
        self.assertEqual(len(r02_findings), 1)

        # Negative case: switch with PQC
        code_neg = """
        void setup_algo(int type) {
            switch(type) {
                case RSA:
                    break;
                case ML_KEM:
                    break;
            }
        }
        """
        fpath_neg = self.create_temp_file(code_neg)
        findings_neg = self.scanner.scan_file(fpath_neg)
        r02_findings_neg = [f for f in findings_neg if f.rule_id == "R02"]
        self.assertEqual(len(r02_findings_neg), 0)

    def test_r02_rigid_algo_selection_if(self):
        # Positive case: if/else-if with classical but no PQC
        code = """
        void init(int code) {
            if (code == RSA) {
                // do rsa
            } else if (code == ECDH) {
                // do ecdh
            }
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r02_findings = [f for f in findings if f.rule_id == "R02"]
        self.assertEqual(len(r02_findings), 1)

    def test_r03_stack_crypto_buffer(self):
        # Positive case: large stack-allocated array with crypto keyword
        code = """
        void encrypt_data() {
            uint8_t signature_buf[2048];
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r03_findings = [f for f in findings if f.rule_id == "R03"]
        self.assertEqual(len(r03_findings), 1)
        self.assertIn("signature_buf", r03_findings[0].message)

        # Negative case: small stack array or non-crypto
        code_neg = """
        void encrypt_data() {
            uint8_t public_key[32]; // R01, not R03
            uint8_t temp_scratch[2048]; // Not crypto-related name
        }
        """
        fpath_neg = self.create_temp_file(code_neg)
        findings_neg = self.scanner.scan_file(fpath_neg)
        r03_findings_neg = [f for f in findings_neg if f.rule_id == "R03"]
        self.assertEqual(len(r03_findings_neg), 0)

    def test_r04_unchecked_crypto_return(self):
        # Positive case: crypto call returns unchecked
        code = """
        void test() {
            OQS_KEM_decaps(ss, ct, sk);
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r04_findings = [f for f in findings if f.rule_id == "R04"]
        self.assertEqual(len(r04_findings), 1)

        # Negative case: return checked
        code_neg = """
        void test() {
            if (OQS_KEM_decaps(ss, ct, sk) != 0) {
                error();
            }
            int rc = OQS_KEM_decaps(ss, ct, sk);
        }
        """
        fpath_neg = self.create_temp_file(code_neg)
        findings_neg = self.scanner.scan_file(fpath_neg)
        r04_findings_neg = [f for f in findings_neg if f.rule_id == "R04"]
        self.assertEqual(len(r04_findings_neg), 0)

    def test_r05_algorithm_specific_api(self):
        # Positive case
        code = """
        void main() {
            OQS_KEM_kyber_768_decaps(ss, ct, sk);
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r05_findings = [f for f in findings if f.rule_id == "R05"]
        self.assertEqual(len(r05_findings), 1)

    def test_r06_unsafe_malloc_keysize(self):
        # Positive case
        code = """
        void test() {
            uint8_t *buf = malloc(pk_len + sk_len);
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r06_findings = [f for f in findings if f.rule_id == "R06"]
        self.assertEqual(len(r06_findings), 1)

    def test_r07_contract_violation_positive(self):
        # Positive case: crypto call captures return and returns it unchecked
        code = """
        int execute_pqc() {
            int ret = OQS_KEM_decaps(ss, ct, sk);
            return ret;
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r07_findings = [f for f in findings if f.rule_id == "R07"]
        self.assertEqual(len(r07_findings), 1)

    def test_r07_contract_violation_negative(self):
        # Negative case: variable checked before return
        code = """
        int execute_pqc() {
            int ret = OQS_KEM_decaps(ss, ct, sk);
            if (ret != 0) {
                return -1;
            }
            return ret;
        }
        """
        fpath = self.create_temp_file(code)
        findings = self.scanner.scan_file(fpath)
        r07_findings = [f for f in findings if f.rule_id == "R07"]
        self.assertEqual(len(r07_findings), 0)

if __name__ == "__main__":
    unittest.main()

