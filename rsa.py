import sys
import json
import os
# pylint: disable=W0612,W0613,W0621,R0914,C0103,C0801
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QGroupBox, QGridLayout, QSpinBox,
                             QTabWidget, QComboBox, QCheckBox, QMessageBox,
                             QSplitter, QFrame, QFileDialog, QProgressBar,
                             QToolTip, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor, QMovie
import math
import unittest
from datetime import datetime

# Try to import advanced math libraries
try:
    from sympy import isprime, mod_inverse as sympy_mod_inverse, Integer

    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False

try:
    from Crypto.Util import number

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class RSACalculator:
    """Core RSA calculation engine with enhanced security"""

    # Minimum recommended prime size for educational purposes
    MIN_PRIME_SIZE = 2
    MIN_SECURE_PRIME = 11  # For real security, this would be much larger

    @staticmethod
    def gcd(a, b):
        """Calculate Greatest Common Divisor"""
        while b:
            a, b = b, a % b
        return a

    @staticmethod
    def mod_inverse(e, phi):
        """Calculate modular inverse of e mod phi"""
        if SYMPY_AVAILABLE:
            try:
                return int(sympy_mod_inverse(e, phi))
            except:
                pass

        def extended_gcd(a, b):
            if a == 0:
                return b, 0, 1
            inner_gcd, inner_x, inner_y = extended_gcd(b % a, a)
            adj_x = inner_y - (b // a) * inner_x
            return inner_gcd, adj_x, inner_x

        gcd_val, inv_x, _ = extended_gcd(e % phi, phi)
        if gcd_val != 1:
            raise ValueError("Modular inverse does not exist")
        return (inv_x % phi + phi) % phi

    @staticmethod
    def is_prime(n):
        """Check if a number is prime"""
        if SYMPY_AVAILABLE:
            return isprime(n)

        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False

        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False
        return True

    @staticmethod
    def validate_prime_pair(p, q):
        """Validate prime pair for RSA"""
        errors = []
        warnings = []

        if not RSACalculator.is_prime(p):
            errors.append(f"{p} is not prime")
        if not RSACalculator.is_prime(q):
            errors.append(f"{q} is not prime")

        if p == q:
            errors.append("p and q must be different primes")

        if p < RSACalculator.MIN_PRIME_SIZE or q < RSACalculator.MIN_PRIME_SIZE:
            errors.append(f"Primes must be at least {RSACalculator.MIN_PRIME_SIZE}")

        if p < RSACalculator.MIN_SECURE_PRIME or q < RSACalculator.MIN_SECURE_PRIME:
            warnings.append(f"For better security, use primes ≥ {RSACalculator.MIN_SECURE_PRIME}")

        n = p * q
        if n < 33:  # Minimum to handle all letters + space
            errors.append("n = p×q must be at least 33 to handle all characters")

        return errors, warnings

    @staticmethod
    def calculate_entropy(n):
        """Calculate approximate entropy bits of modulus n"""
        return math.log2(n)

    @staticmethod
    def encrypt_block(m, e, n, use_large_numbers=False):
        """Encrypt a single block using RSA"""
        # Always encrypt every value using RSA formula: pow(m, e, n)
        if use_large_numbers and SYMPY_AVAILABLE:
            return int(pow(Integer(m), Integer(e), Integer(n)))
        return pow(m, e, n)

    @staticmethod
    def decrypt_block(c, d, n, use_large_numbers=False):
        """Decrypt a single block using RSA"""
        if use_large_numbers and SYMPY_AVAILABLE:
            return int(pow(Integer(c), Integer(d), Integer(n)))
        return pow(c, d, n)

    @staticmethod
    def generate_secure_primes(bits):
        """Generate secure prime numbers (if libraries available)"""
        if CRYPTO_AVAILABLE:
            p = number.getPrime(bits)
            q = number.getPrime(bits)
            while p == q:
                q = number.getPrime(bits)
            return p, q
        else:
            # Fallback: return small example primes
            primes = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
            import random
            p = random.choice(primes)
            q = random.choice([x for x in primes if x != p])
            return p, q


class RSAWorker(QThread):
    """Worker thread for RSA operations"""
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, operation, **kwargs):
        super().__init__()
        self.operation = operation
        self.kwargs = kwargs

    def run(self):
        try:
            if self.operation == "encrypt":
                result = self.encrypt_message()
            elif self.operation == "decrypt":
                result = self.decrypt_message()
            else:
                result = ""
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    # The following logic improves both mathematical correctness and user experience by explicitly aligning the symbol set with password-strength/entropy principles.
    def encrypt_message(self):
        text = self.kwargs['text']
        e = self.kwargs['e']
        n = self.kwargs['n']
        include_punctuation = self.kwargs.get('include_punctuation', False)
        use_large = self.kwargs.get('use_large_numbers', False)

        # Character mapping and encryption logic:
        # 1. Letters (A-Z, a-z) are mapped to numbers 1–26 (A=1, ..., Z=26), then encrypted with RSA: c = m^e mod n.
        #    - This uses the standard mathematical RSA formula, ensuring that each symbol's numeric representation is preserved through encryption.
        # 2. Only the five allowed punctuation characters ('.', ',', '!', '?', ';') are optionally included, mapped to 27–31.
        #    - This maintains a fixed numeric mapping and prevents ambiguity in decryption.
        # 3. All other characters (including quotes, brackets, or symbols) are skipped unless punctuation inclusion is enabled.
        #    - Skipped characters are collected and reported in the output warning to inform the user.
        # 4. This approach models password/entropy principles by strictly controlling the set of allowed symbols,
        #    making the mapping explicit and predictable, and improving both mathematical and user experience aspects.
        #    It also helps users understand which characters contribute to the "entropy" of the encrypted message.
        result = []
        trace = []
        original_numbers = []
        skipped_chars = []
        # For reporting which punctuation was skipped (if any)

        for char in text:
            if char.isalpha():
                number = ord(char.lower()) - 96  # a=1, b=2, ..., z=26
                encrypted = RSACalculator.encrypt_block(number, e, n, use_large)
                result.append(encrypted)
                trace.append(f"Encrypting: {number} → {encrypted}")
                original_numbers.append(number)
            elif char in {'.', ',', '!', '?', ';'}:
                if include_punctuation:
                    punct_map = {'.': 27, ',': 28, '!': 29, '?': 30, ';': 31}
                    number = punct_map[char]
                    encrypted = RSACalculator.encrypt_block(number, e, n, use_large)
                    result.append(encrypted)
                    trace.append(f"Encrypting: {number} → {encrypted}")
                    original_numbers.append(number)
                else:
                    skipped_chars.append(char)
            # Handle spaces as numeric 32 rather than skipping them
            elif char.isspace():
                # Map space to 32 and encrypt
                number = 32
                encrypted = RSACalculator.encrypt_block(number, e, n, use_large)
                result.append(encrypted)
                trace.append(f"Encrypting: {number} → {encrypted}")
                original_numbers.append(number)
            else:
                skipped_chars.append(char)

            # Progress bar update
            if len(text) > 0:
                self.progress_value.emit(int((len(result)) / max(1, len(text)) * 100))
            # Emit progress only if not duplicate
            if trace:
                last_trace = trace[-1]
                if not hasattr(self, "_last_emitted_trace") or self._last_emitted_trace != last_trace:
                    self.progress.emit(last_trace)
                    self._last_emitted_trace = last_trace

        # Format output
        plain_formatted = ' '.join(f"{num:02d}" for num in original_numbers)
        encrypted_formatted = ' '.join(f"{num:02d}" for num in result)
        output = f"Original numbers: {plain_formatted}\nEncrypted: {encrypted_formatted}"
        if skipped_chars and not include_punctuation:
            unique_skipped = ''.join(sorted(set(skipped_chars)))
            output += (
                "\n\n[Warning] The following character(s) were skipped due to punctuation settings: "
                f"{unique_skipped}\n"
                "To include punctuation, check the 'Include punctuation' box."
            )
        return output

    def decrypt_message(self):
        encrypted_text = self.kwargs['encrypted_text']
        d = self.kwargs['d']
        n = self.kwargs['n']
        include_punctuation = self.kwargs.get('include_punctuation', False)
        use_large = self.kwargs.get('use_large_numbers', False)

        # Parse encrypted numbers
        encrypted_nums = []
        for num_str in encrypted_text.split():
            try:
                encrypted_nums.append(int(num_str))
            except ValueError:
                continue

        total_steps = len(encrypted_nums)

        # Decrypt each number
        decrypted = []
        for i, enc_num in enumerate(encrypted_nums):
            dec_num = RSACalculator.decrypt_block(enc_num, d, n, use_large)
            decrypted.append(dec_num)
            self.progress.emit(f"Decrypting: {enc_num} → {dec_num}")
            self.progress_value.emit(int((i + 1) / total_steps * 100))

        # Convert back to text
        message = ""
        for num in decrypted:
            if 1 <= num <= 26:
                message += chr(num - 1 + ord('A'))
            elif num == 32:
                message += ' '
            elif include_punctuation and 27 <= num <= 31:
                punctuation_map = {27: '.', 28: ',', 29: '!', 30: '?', 31: ';'}
                message += punctuation_map.get(num, '')

        return f"Decrypted numbers: {' '.join(f'{num:02d}' for num in decrypted)}\nMessage: {message}"

#Class that define the animated progress bar
class AnimatedProgressBar(QProgressBar):
    """Custom animated progress bar"""

    def __init__(self):
        super().__init__()
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Animation
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def set_value_animated(self, value):
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()

#class for the main window of the RSA application.
class RSAMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Pre-declare instance attributes
        self.tabs = None
        self.progress_bar = None
        self.large_numbers_check = None
        self.generate_primes_btn = None
        self.p_spin = None
        self.q_spin = None
        self.validate_primes_btn = None
        self.security_label = None
        self.security_value = None
        self.entropy_label = None
        self.entropy_value = None
        self.n_label = None
        self.phi_label = None
        self.e_spin = None
        self.d_label = None
        self.calculate_keys_btn = None
        self.details_text = None
        self.export_keys_btn = None
        self.import_keys_btn = None
        self.encrypt_input = None
        self.include_punct_encrypt = None
        self.save_encrypted_btn = None
        self.encrypt_btn = None
        self.encrypt_output = None
        self.decrypt_input = None
        self.include_punct_decrypt = None
        self.save_decrypted_btn = None
        self.decrypt_btn = None
        self.decrypt_output = None
        # End pre-declarations
        self.worker = None
        self.setWindowTitle("Advanced RSA Encryption/Decryption Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Apply enhanced dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                background-color: #3c3c3c;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QTextEdit, QSpinBox {
                background-color: #1e1e1e;
                border: 1px solid #555;
                color: #ffffff;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
            QPushButton:pressed {
                background-color: #0a5d61;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #0d7377;
                border-radius: 3px;
            }
            QToolTip {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Setup tab
        setup_tab = QWidget()
        self.tabs.addTab(setup_tab, "RSA Setup")
        self.create_setup_tab(setup_tab)

        # Encrypt tab
        encrypt_tab = QWidget()
        self.tabs.addTab(encrypt_tab, "Encrypt")
        self.create_encrypt_tab(encrypt_tab)

        # Decrypt tab containing the decrypt tab
        decrypt_tab = QWidget()
        self.tabs.addTab(decrypt_tab, "Decrypt")
        self.create_decrypt_tab(decrypt_tab)

        # Example tab containing examples and help
        example_tab = QWidget()
        self.tabs.addTab(example_tab, "Examples & Help")
        self.create_example_tab(example_tab)

        # Status bar with progress
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("color: #ffffff; background-color: #1e1e1e;")

    def create_setup_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Security options
        security_group = QGroupBox("Security Options")
        security_layout = QHBoxLayout()

        self.large_numbers_check = QCheckBox("Use arbitrary-precision arithmetic")
        self.large_numbers_check.setToolTip(
            "Enable this for very large numbers (requires SymPy)"
        )
        self.large_numbers_check.setEnabled(SYMPY_AVAILABLE)
        if not SYMPY_AVAILABLE:
            self.large_numbers_check.setText("Use arbitrary-precision arithmetic (SymPy not installed)")
        security_layout.addWidget(self.large_numbers_check)

        self.generate_primes_btn = QPushButton("Generate Secure Primes")
        self.generate_primes_btn.setToolTip(
            "Generate cryptographically secure prime numbers"
        )
        self.generate_primes_btn.clicked.connect(self.generate_secure_primes)
        security_layout.addWidget(self.generate_primes_btn)

        security_layout.addStretch()
        security_group.setLayout(security_layout)
        layout.addWidget(security_group)

        # Prime numbers section
        prime_group = QGroupBox("Prime Numbers")
        prime_layout = QGridLayout()

        p_label = QLabel("p (prime):")
        p_label.setToolTip("First prime number for RSA key generation")
        prime_layout.addWidget(p_label, 0, 0)

        self.p_spin = QSpinBox()
        self.p_spin.setRange(2, 10000)
        self.p_spin.setValue(3)
        self.p_spin.setToolTip("Must be a prime number different from q")
        prime_layout.addWidget(self.p_spin, 0, 1)

        q_label = QLabel("q (prime):")
        q_label.setToolTip("Second prime number for RSA key generation")
        prime_layout.addWidget(q_label, 0, 2)

        self.q_spin = QSpinBox()
        self.q_spin.setRange(2, 10000)
        self.q_spin.setValue(11)
        self.q_spin.setToolTip("Must be a prime number different from p")
        prime_layout.addWidget(self.q_spin, 0, 3)

        self.validate_primes_btn = QPushButton("Validate Primes")
        self.validate_primes_btn.setToolTip("Check if p and q are valid primes for RSA")
        self.validate_primes_btn.clicked.connect(self.validate_primes)
        prime_layout.addWidget(self.validate_primes_btn, 0, 4)

        # Security indicator
        self.security_label = QLabel("Security Level: ")
        self.security_value = QLabel("Low")
        self.security_value.setStyleSheet("color: #e74c3c; font-weight: bold;")
        prime_layout.addWidget(self.security_label, 1, 0)
        prime_layout.addWidget(self.security_value, 1, 1)

        self.entropy_label = QLabel("Entropy bits: ")
        self.entropy_value = QLabel("~5 bits")
        self.entropy_value.setToolTip("Approximate entropy of the modulus n")
        prime_layout.addWidget(self.entropy_label, 1, 2)
        prime_layout.addWidget(self.entropy_value, 1, 3)

        prime_group.setLayout(prime_layout)
        layout.addWidget(prime_group)

        # Key calculation section
        key_group = QGroupBox("Key Calculation")
        key_layout = QGridLayout()

        n_label = QLabel("n = p × q:")
        n_label.setToolTip("RSA modulus - product of the two primes")
        key_layout.addWidget(n_label, 0, 0)
        self.n_label = QLabel("33")
        self.n_label.setStyleSheet("font-weight: bold; color: #14a085;")
        key_layout.addWidget(self.n_label, 0, 1)

        phi_label = QLabel("φ(n) = (p-1)(q-1):")
        phi_label.setToolTip("Euler's totient function - number of integers coprime to n")
        key_layout.addWidget(phi_label, 1, 0)
        self.phi_label = QLabel("20")
        self.phi_label.setStyleSheet("font-weight: bold; color: #14a085;")
        key_layout.addWidget(self.phi_label, 1, 1)

        e_label = QLabel("Public key e:")
        e_label.setToolTip("Public exponent - must be coprime with φ(n)")
        key_layout.addWidget(e_label, 2, 0)
        self.e_spin = QSpinBox()
        self.e_spin.setRange(2, 10000)
        self.e_spin.setValue(3)
        self.e_spin.setToolTip("Common values: 3, 5, 17, 257, 65537")
        key_layout.addWidget(self.e_spin, 2, 1)

        d_label = QLabel("Private key d:")
        d_label.setToolTip("Private exponent - modular inverse of e modulo φ(n)")
        key_layout.addWidget(d_label, 3, 0)
        self.d_label = QLabel("7")
        self.d_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        key_layout.addWidget(self.d_label, 3, 1)

        self.calculate_keys_btn = QPushButton("Calculate Keys")
        self.calculate_keys_btn.setToolTip("Calculate RSA key pair from p, q, and e")
        self.calculate_keys_btn.clicked.connect(self.calculate_keys)
        key_layout.addWidget(self.calculate_keys_btn, 4, 0, 1, 2)

        key_group.setLayout(key_layout)
        layout.addWidget(key_group)

        # Key details
        details_group = QGroupBox("Calculation Details")
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        details_layout = QVBoxLayout()
        details_layout.addWidget(self.details_text)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Character mapping reference
        mapping_group = QGroupBox("Character Mapping Reference")
        mapping_layout = QVBoxLayout()
        mapping_text = QTextEdit()
        mapping_text.setReadOnly(True)
        mapping_text.setMaximumHeight(100)
        mapping_text.setPlainText(
            "A=01, B=02, C=03, ..., Z=26\n"
            "Space=32\n"
            "Optional punctuation: .=27, ,=28, !=29, ?=30, ;=31"
        )
        mapping_layout.addWidget(mapping_text)
        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)

        # Export buttons
        export_layout = QHBoxLayout()
        self.export_keys_btn = QPushButton("Export Keys")
        self.export_keys_btn.setToolTip("Save current RSA keys to file")
        self.export_keys_btn.clicked.connect(self.export_keys)
        export_layout.addWidget(self.export_keys_btn)

        self.import_keys_btn = QPushButton("Import Keys")
        self.import_keys_btn.setToolTip("Load RSA keys from file")
        self.import_keys_btn.clicked.connect(self.import_keys)
        export_layout.addWidget(self.import_keys_btn)

        export_layout.addStretch()
        layout.addLayout(export_layout)

        # Initial calculation
        self.calculate_keys()

    def create_encrypt_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Input section
        input_group = QGroupBox("Message to Encrypt")
        input_layout = QVBoxLayout()

        self.encrypt_input = QTextEdit()
        self.encrypt_input.setPlaceholderText("Enter your message here...")
        self.encrypt_input.setMaximumHeight(100)
        input_layout.addWidget(self.encrypt_input)

        options_layout = QHBoxLayout()
        self.include_punct_encrypt = QCheckBox("Include punctuation")
        self.include_punct_encrypt.setToolTip("Enable punctuation characters (.,!?;)")
        options_layout.addWidget(self.include_punct_encrypt)

        options_layout.addStretch()

        self.save_encrypted_btn = QPushButton("Save Result")
        self.save_encrypted_btn.setToolTip("Save encrypted message to file")
        self.save_encrypted_btn.clicked.connect(lambda: self.save_result("encrypt"))
        self.save_encrypted_btn.setEnabled(False)
        options_layout.addWidget(self.save_encrypted_btn)

        self.encrypt_btn = QPushButton("Encrypt Message")
        self.encrypt_btn.setToolTip("Encrypt the message using current RSA keys")
        self.encrypt_btn.clicked.connect(self.encrypt_message)
        options_layout.addWidget(self.encrypt_btn)

        input_layout.addLayout(options_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Output section
        output_group = QGroupBox("Encryption Result")
        output_layout = QVBoxLayout()

        self.encrypt_output = QTextEdit()
        self.encrypt_output.setReadOnly(True)
        output_layout.addWidget(self.encrypt_output)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

    #Defines the decrypt tab to take simple encrypted input and then decrypt it.
    def create_decrypt_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Input section
        input_group = QGroupBox("Encrypted Message")
        input_layout = QVBoxLayout()

        self.decrypt_input = QTextEdit()
        self.decrypt_input.setPlaceholderText("Enter encrypted numbers separated by spaces...")
        self.decrypt_input.setMaximumHeight(100)
        input_layout.addWidget(self.decrypt_input)

        # Add external input for custom-pasted encrypted messages
        self.external_input = QLineEdit()
        self.external_input.setPlaceholderText("Paste encrypted numbers (e.g. 27 03 16 ...)")
        self.decrypt_external_btn = QPushButton("Decrypt External Message")
        self.decrypt_external_btn.clicked.connect(self.handle_decrypt_external)
        input_layout.addWidget(self.external_input)
        input_layout.addWidget(self.decrypt_external_btn)

        options_layout = QHBoxLayout()
        self.include_punct_decrypt = QCheckBox("Message includes punctuation")
        self.include_punct_decrypt.setToolTip("Check if message contains punctuation")
        options_layout.addWidget(self.include_punct_decrypt)

        options_layout.addStretch()

        self.save_decrypted_btn = QPushButton("Save Result")
        self.save_decrypted_btn.setToolTip("Save decrypted message to file")
        self.save_decrypted_btn.clicked.connect(lambda: self.save_result("decrypt"))
        self.save_decrypted_btn.setEnabled(False)
        options_layout.addWidget(self.save_decrypted_btn)

        self.decrypt_btn = QPushButton("Decrypt Message")
        self.decrypt_btn.setToolTip("Decrypt the message using current RSA keys")
        self.decrypt_btn.clicked.connect(self.decrypt_message)
        options_layout.addWidget(self.decrypt_btn)

        input_layout.addLayout(options_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Output section
        output_group = QGroupBox("Decryption Result")
        output_layout = QVBoxLayout()

        self.decrypt_output = QTextEdit()
        self.decrypt_output.setReadOnly(True)
        output_layout.addWidget(self.decrypt_output)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

    def handle_decrypt_external(self):
        cipher_text = self.external_input.text()
        try:
            d = int(self.d_label.text())
            n = int(self.n_label.text())
            result = decrypt_custom_message(cipher_text, d, n)
            QMessageBox.information(self, "Decrypted Output", f"Decrypted Message:\n{result}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def create_example_tab(self, parent):
        layout = QVBoxLayout(parent)

        examples_text = QTextEdit()
        examples_text.setReadOnly(True)
        examples_text.setHtml("""
        <h2 style="color: #14a085;">RSA Encryption Examples</h2>

        <h3 style="color: #e74c3c;">Example 1: "A CAB"</h3>
        <p><b>Setup:</b> p=3, q=11, e=3, n=33, d=7</p>
        <p><b>Text to numbers:</b> A=01, Space=32, C=03, A=01, B=02</p>
        <p><b>Original:</b> 01 32 03 01 02</p>
        <p><b>Encrypted:</b> 01 32 27 01 08</p>

        <h3 style="color: #e74c3c;">How to Calculate d:</h3>
        <ol>
        <li>Calculate n = p × q</li>
        <li>Calculate φ(n) = (p-1) × (q-1)</li>
        <li>Choose e such that gcd(e, φ(n)) = 1</li>
        <li>Find d such that (e × d) mod φ(n) = 1</li>
        </ol>

        <h3 style="color: #e74c3c;">Security Tips:</h3>
        <ul>
        <li>Always use different primes (p ≠ q)</li>
        <li>For educational use: primes ≥ 11 recommended</li>
        <li>For real security: use primes with hundreds of digits</li>
        <li>Common e values: 3, 17, 65537</li>
        <li>Keep your private key d secret!</li>
        </ul>

        <h3 style="color: #e74c3c;">Features:</h3>
        <ul>
        <li><b>Input Validation:</b> Ensures p and q are valid primes</li>
        <li><b>Security Indicators:</b> Shows entropy and security level</li>
        <li><b>Export/Import:</b> Save and load key configurations</li>
        <li><b>Progress Tracking:</b> Visual feedback during operations</li>
        <li><b>Large Number Support:</b> Optional arbitrary-precision arithmetic</li>
        </ul>

        <h3 style="color: #e74c3c;">Keyboard Shortcuts:</h3>
        <ul>
        <li><b>Ctrl+S:</b> Save current result</li>
        <li><b>Ctrl+O:</b> Import keys</li>
        <li><b>F5:</b> Recalculate keys</li>
        </ul>
        """)

        layout.addWidget(examples_text)

        # Add test runner button
        test_btn = QPushButton("Run Unit Tests")
        test_btn.setToolTip("Run built-in unit tests for RSA calculator")
        test_btn.clicked.connect(self.run_unit_tests)
        layout.addWidget(test_btn)
    #Def generate secure primes checks if the required libraries are available
    ##and generates secure primes
    def generate_secure_primes(self):
        """Generate cryptographically secure primes"""
        try:
            if CRYPTO_AVAILABLE or SYMPY_AVAILABLE:
                p, q = RSACalculator.generate_secure_primes(16)  # 16-bit primes for demo
                self.p_spin.setValue(p)
                self.q_spin.setValue(q)
                self.calculate_keys()
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Primes Generated")
                msg_box.setText(f"Generated secure primes:\np = {p}\nq = {q}")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #2b2b2b;
                        color: #ffffff;
                        font-weight: bold;
                    }
                    QPushButton {
                        background-color: #006064;
                        color: white;
                        border-radius: 4px;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background-color: #00838f;
                    }
                """)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Library Not Available")
                msg_box.setText("Install pycryptodome or sympy for secure prime generation")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #2b2b2b;
                        color: #ffffff;
                        font-weight: bold;
                    }
                    QPushButton {
                        background-color: #006064;
                        color: white;
                        border-radius: 4px;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background-color: #00838f;
                    }
                """)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Generation Error")
            msg_box.setText(str(e))
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #006064;
                    color: white;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #00838f;
                }
            """)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
    #Validation
    def validate_primes(self):
        p = self.p_spin.value()
        q = self.q_spin.value()

        errors, warnings = RSACalculator.validate_prime_pair(p, q)

        if not errors and not warnings:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Prime Validation")
            msg_box.setText(f"✓ Both {p} and {q} are valid primes!\nNo security issues detected.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #006064;
                    color: white;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #00838f;
                }
            """)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        elif errors:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Prime Validation Failed")
            msg_box.setText("✗ Critical issues:\n" + "\n".join(errors))
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #006064;
                    color: white;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #00838f;
                }
            """)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        else:
            msg = "✓ Primes are valid but:\n" + "\n".join(warnings)
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Prime Validation")
            msg_box.setText(msg)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #006064;
                    color: white;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #00838f;
                }
            """)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

    def calculate_keys(self):
        try:
            p = self.p_spin.value()
            q = self.q_spin.value()
            e = self.e_spin.value()

            # Validate primes first
            errors, warnings = RSACalculator.validate_prime_pair(p, q)
            if errors:
                raise ValueError("\n".join(errors))

            # Calculate n and phi
            n = p * q
            phi = (p - 1) * (q - 1)

            # Update labels
            self.n_label.setText(str(n))
            self.phi_label.setText(str(phi))

            # Calculate entropy and security level
            #Gives approximate bits of entropy
            entropy = RSACalculator.calculate_entropy(n)
            self.entropy_value.setText(f"~{entropy:.1f} bits")

            if entropy < 10:
                self.security_value.setText("Very Low")
                self.security_value.setStyleSheet("color: #e74c3c; font-weight: bold;")
            elif entropy < 20:
                self.security_value.setText("Low")
                self.security_value.setStyleSheet("color: #e67e22; font-weight: bold;")
            elif entropy < 40:
                self.security_value.setText("Medium")
                self.security_value.setStyleSheet("color: #f39c12; font-weight: bold;")
            else:
                self.security_value.setText("Good (Educational)")
                self.security_value.setStyleSheet("color: #27ae60; font-weight: bold;")

            # Check if e is valid
            if RSACalculator.gcd(e, phi) != 1:
                raise ValueError(f"e={e} is not coprime with φ(n)={phi}")

            # Calculate d
            use_large = self.large_numbers_check.isChecked()
            d = RSACalculator.mod_inverse(e, phi)
            self.d_label.setText(str(d))

            # Show calculation details
            details = f"""Calculation Steps:
1. n = p × q = {p} × {q} = {n}
2. φ(n) = (p-1) × (q-1) = {p - 1} × {q - 1} = {phi}
3. Public key e = {e} (must be coprime with φ(n))
4. Private key d = {d} (calculated as modular inverse of e mod φ(n))
5. Verification: (e × d) mod φ(n) = ({e} × {d}) mod {phi} = {(e * d) % phi}
6. Key size: {entropy:.1f} bits of entropy

Security Assessment:
- Primes are {"different" if p != q else "THE SAME (INSECURE!)"}
- Modulus n = {n} {"(sufficient for all characters)" if n >= 33 else "(TOO SMALL!)"}
- Using {"arbitrary-precision arithmetic" if use_large else "standard arithmetic"}"""

            self.details_text.setPlainText(details)
            self.statusBar().showMessage("Keys calculated successfully")

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", str(e))
            self.statusBar().showMessage("Error calculating keys")

    def encrypt_message(self):
        try:
            text = self.encrypt_input.toPlainText()
            if not text:
                QMessageBox.warning(self, "Input Error", "Please enter a message to encrypt")
                return

            e = self.e_spin.value()
            n = int(self.n_label.text())
            include_punct = self.include_punct_encrypt.isChecked()
            use_large = self.large_numbers_check.isChecked()

            # Clear output and show progress
            self.encrypt_output.clear()
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)

            # Create worker thread
            #Imporant for large text encryption
            self.worker = RSAWorker("encrypt", text=text, e=e, n=n,
                                    include_punctuation=include_punct,
                                    use_large_numbers=use_large)
            self.worker.progress.connect(lambda msg: self.encrypt_output.append(msg))
            self.worker.progress_value.connect(self.progress_bar.set_value_animated)
            self.worker.finished.connect(self.on_encrypt_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

            self.encrypt_btn.setEnabled(False)
            self.statusBar().showMessage("Encrypting...")

        except Exception as e:
            QMessageBox.critical(self, "Encryption Error", str(e))

    def decrypt_message(self):
        try:
            encrypted_text = self.decrypt_input.toPlainText()
            if not encrypted_text:
                QMessageBox.warning(self, "Input Error", "Please enter encrypted numbers")
                return

            d = int(self.d_label.text())
            n = int(self.n_label.text())
            include_punct = self.include_punct_decrypt.isChecked()
            use_large = self.large_numbers_check.isChecked()

            # Clear output and show progress
            self.decrypt_output.clear()
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)

            # Create worker thread
            self.worker = RSAWorker("decrypt", encrypted_text=encrypted_text,
                                    d=d, n=n, include_punctuation=include_punct,
                                    use_large_numbers=use_large)
            self.worker.progress.connect(lambda msg: self.decrypt_output.append(msg))
            self.worker.progress_value.connect(self.progress_bar.set_value_animated)
            self.worker.finished.connect(self.on_decrypt_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

            self.decrypt_btn.setEnabled(False)
            self.statusBar().showMessage("Decrypting...")

        except Exception as e:
            QMessageBox.critical(self, "Decryption Error", str(e))

    def on_encrypt_finished(self, result):
        self.encrypt_output.append("\n" + "=" * 50 + "\n")
        self.encrypt_output.append(result)
        self.encrypt_btn.setEnabled(True)
        self.save_encrypted_btn.setEnabled(True)
        self.progress_bar.set_value_animated(100)
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        self.statusBar().showMessage("Encryption complete")

    def on_decrypt_finished(self, result):
        self.decrypt_output.append("\n" + "=" * 50 + "\n")
        self.decrypt_output.append(result)
        self.decrypt_btn.setEnabled(True)
        self.save_decrypted_btn.setEnabled(True)
        self.progress_bar.set_value_animated(100)
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        self.statusBar().showMessage("Decryption complete")

    def on_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
        self.encrypt_btn.setEnabled(True)
        self.decrypt_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Error occurred")

    def export_keys(self):
        """Export RSA keys to JSON file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export RSA Keys", "", "JSON Files (*.json)"
            )
            if filename:
                keys = {
                    "p": self.p_spin.value(),
                    "q": self.q_spin.value(),
                    "e": self.e_spin.value(),
                    "d": int(self.d_label.text()),
                    "n": int(self.n_label.text()),
                    "phi": int(self.phi_label.text()),
                    "timestamp": datetime.now().isoformat()
                }
                with open(filename, 'w') as f:
                    json.dump(keys, f, indent=2)  # type: ignore
                QMessageBox.information(self, "Export Successful",
                                        f"Keys exported to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_keys(self):
        """Import RSA keys from JSON file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Import RSA Keys", "", "JSON Files (*.json)"
            )
            if filename:
                with open(filename, 'r') as f:
                    keys = json.load(f)  # type: ignore

                self.p_spin.setValue(keys.get('p', 3))
                self.q_spin.setValue(keys.get('q', 11))
                self.e_spin.setValue(keys.get('e', 3))

                self.calculate_keys()
                QMessageBox.information(self, "Import Successful",
                                        f"Keys imported from {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def save_result(self, tab_type):
        """Save encryption/decryption result to file"""
        try:
            if tab_type == "encrypt":
                content = self.encrypt_output.toPlainText()
                default_name = "encrypted_message.txt"
            else:
                content = self.decrypt_output.toPlainText()
                default_name = "decrypted_message.txt"

            if not content:
                QMessageBox.warning(self, "No Content", "No content to save")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Result", default_name, "Text Files (*.txt)"
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write(content)
                QMessageBox.information(self, "Save Successful",
                                        f"Result saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def run_unit_tests(self):
        """Run built-in unit tests"""
        dialog = None
        result_text = None
        try:
            # Create test dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Unit Test Results")
            dialog.setModal(True)
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)
            result_text = QTextEdit()
            result_text.setReadOnly(True)
            layout.addWidget(result_text)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            buttons.accepted.connect(dialog.accept)
            layout.addWidget(buttons)

            # Run tests
            result_text.append("Running RSA Calculator Unit Tests...\n")

            # Test 1: Prime validation
            result_text.append("Test 1: Prime number validation")
            assert RSACalculator.is_prime(3) == True
            assert RSACalculator.is_prime(4) == False
            assert RSACalculator.is_prime(11) == True
            result_text.append("✓ Passed\n")

            # Test 2: GCD calculation
            result_text.append("Test 2: GCD calculation")
            assert RSACalculator.gcd(20, 3) == 1
            assert RSACalculator.gcd(12, 8) == 4
            result_text.append("✓ Passed\n")

            # Test 3: Modular inverse
            result_text.append("Test 3: Modular inverse")
            assert RSACalculator.mod_inverse(3, 20) == 7
            result_text.append("✓ Passed\n")

            # Test 4: Example encryption/decryption
            result_text.append("Test 4: 'A CAB' example")
            p, q, e = 3, 11, 3
            n = p * q
            d = 7

            # Test encryption
            plain_nums = [1, 32, 3, 1, 2]  # A SPACE C A B
            expected_enc = [1, 32, 27, 1, 8]

            for i, plain in enumerate(plain_nums):
                enc = RSACalculator.encrypt_block(plain, e, n)
                assert enc == expected_enc[i], f"Expected {expected_enc[i]}, got {enc}"
            result_text.append("✓ Encryption passed\n")

            # Test decryption
            for i, enc in enumerate(expected_enc):
                dec = RSACalculator.decrypt_block(enc, d, n)
                assert dec == plain_nums[i], f"Expected {plain_nums[i]}, got {dec}"
            result_text.append("✓ Decryption passed\n")

            # Test 5: Security validation
            result_text.append("Test 5: Security validation")
            errors, warnings = RSACalculator.validate_prime_pair(3, 3)
            assert len(errors) > 0  # Should have error for p == q
            errors, warnings = RSACalculator.validate_prime_pair(3, 11)
            assert len(errors) == 0  # Should be valid
            result_text.append("✓ Passed\n")

            result_text.append("\n" + "=" * 50)
            result_text.append("\nAll tests passed successfully! ✓")

            dialog.exec()

        except AssertionError as e:
            if result_text is not None:
                result_text.append(f"\n✗ Test failed: {e}")
                dialog.exec()
            else:
                QMessageBox.critical(self, "Test Error", f"Test failed: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Test Error", f"Error running tests: {e}")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_S:
                # Save current result
                if self.tabs.currentIndex() == 1:  # Encrypt tab
                    self.save_result("encrypt")
                elif self.tabs.currentIndex() == 2:  # Decrypt tab
                    self.save_result("decrypt")
            elif event.key() == Qt.Key.Key_O:
                self.import_keys()
        elif event.key() == Qt.Key.Key_F5:
            self.calculate_keys()


def main():
    app = QApplication(sys.argv)
    window = RSAMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# Utility function for custom decryption of space-separated cipher numbers
def decrypt_custom_message(cipher_text: str, d: int, n: int) -> str:
    """
    Decrypts space-separated RSA cipher numbers using private key (d, n)
    and your A=01–Z=26, space=32 mapping.
    """
    cipher_numbers = list(map(int, cipher_text.strip().split()))
    decoded_numbers = [(pow(c, d, n)) for c in cipher_numbers]

    mapping = {i: chr(64 + i) for i in range(1, 27)}
    mapping[32] = ' '
    mapping.update({27: '?', 28: '!', 29: ',', 30: '.', 31: ';'})

    message = ''.join(mapping.get(num, '?') for num in decoded_numbers)
    return message


# --- Encryption logic with punctuation control ---
from typing import List

def encrypt_message(message: str, include_punctuation: bool = False) -> List[int]:
    import string
    if not include_punctuation:
        message = ''.join(c for c in message if c in string.ascii_letters + string.digits + ' ')
    # ... (rest of logic for mapping message to numbers and encrypting)