import unittest

from backend.calculator import CalculationError, calculate


class CalculatorTests(unittest.TestCase):
    def test_arithmetic_and_precedence(self):
        cases = {
            "2 + 3 × 4": "14",
            "(2 + 3) * 4": "20",
            "10 ÷ 4": "2.5",
            "0.1 + 0.2": "0.3",
            "100 - 25": "75",
            ".5 + 1.": "1.5",
            "2^3^2": "512",
            "-2^2": "-4",
            "(-2)^2": "4",
            "2^-2": "0.25",
            "5**2": "25",
            "200 × 10%": "20",
            "(50+25)%": "0.75",
            "100 + 10%": "100.1",
            "-0": "0",
            "1 / 3": "0.3333333333333333333333333333",
            "1e16 + 1": "1.0000000000000001e+16",
            "1e-9 * 2": "2e-9",
            "1.12345678901234567890123456789": "1.123456789012345678901234568",
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(calculate(expression), expected)

    def test_rejects_invalid_or_unsafe_expressions(self):
        expressions = [
            "", "   ", "1/0", "0^-1", "0^0", "2+", "(2+3", "2+3)",
            "2(3)", "1..2", "2^^3", "2^0.5", "2^101", "1e101", "1e-101",
            "1e100 * 10", "1e-100^100", "1.00000000000000000000000000001e100",
            "__import__('os')", "[1, 2]", "abs(-1)",
            "9" * 257, "(" * 25 + "1" + ")" * 25, "+" * 129 + "1",
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculationError):
                    calculate(expression)

    def test_results_can_be_reused_without_losing_precision(self):
        result = calculate("9007199254740992 + 1")
        self.assertEqual(result, "9007199254740993")
        self.assertEqual(calculate(f"{result} + 1"), "9007199254740994")
        scientific = calculate("1e20 * 2")
        self.assertEqual(calculate(f"{scientific} / 2"), "1e+20")


if __name__ == "__main__":
    unittest.main()
