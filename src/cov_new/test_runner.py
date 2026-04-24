from pathlib import Path
from cov_new.filepaths import Filepaths

class TestRunner:
    """
    Executes tests using an instrumented LLVM build.
    The tests may be LLVM lit-tests or standalone .ll/.bc files.
    """
    def __init__(self, mode: str, filepaths: Filepaths):
        self.mode: str = mode
        self.filepaths: Filepaths = filepaths

    def run(self):
        if self.mode == "lit":
            self.run_lit_tests()
        elif self.mode == "standalone":
            self.run_standalone_tests()
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def run_lit_tests(self):
        pass

    def run_standalone_tests(self):
        pass