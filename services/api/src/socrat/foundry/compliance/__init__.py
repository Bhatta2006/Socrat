"""Resource permissions and network boundaries; remote material is never instructions."""


class PolicyBlocked(RuntimeError):
    def __init__(self, code: str):
        # Callers pass fixed internal reason codes, never remote error messages.
        super().__init__(code if code.isidentifier() and len(code) <= 64 else "policy_blocked")
