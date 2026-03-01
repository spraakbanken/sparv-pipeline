"""Health check for Sparv modules."""

from __future__ import annotations

import inspect

from sparv.api.classes import BaseOutput
from sparv.core import registry
from sparv.core.console import console


class HealthCheck:
    """A class for running health checks on all installed Sparv modules."""

    def __init__(self) -> None:
        """Initialize the health check class."""
        self.all_modules = []
        self.passed_checks = 0
        self.failed_checks = 0

    def run(self) -> int:
        """Find all modules and run all health checks.

        Returns:
            The number of failed checks.
        """
        console.print("[b]Running Sparv Plugin Health Check...[/b]\n")
        self.all_modules = registry.find_modules(find_custom=True, skip_language_check=True)

        for module_name, mod_info in sorted(registry.modules.items()):
            self._check_module(module_name, mod_info)

        console.print("\n[b]Health Check Summary:[/b]")
        if self.failed_checks == 0:
            console.print(f"[green]✔ All {self.passed_checks} checks passed. Everything looks good![/green]")
        else:
            console.print(f"[red]✖ {self.failed_checks} check{'s' if self.failed_checks > 1 else ''} failed.[/red]")
        return self.failed_checks

    def _check_module(self, module_name: str, mod_info: registry.Module) -> None:
        """Run checks on a single module.

        Args:
            module_name: The name of the module to check.
            mod_info: The module information to check.
        """
        console.print(f"[b]Checking module:[/b] [cyan]{module_name}[/cyan]")
        has_error = False

        # Check 1: Module has a description
        if not mod_info.description:
            self._log_error("Module is missing a description (`__description__` or docstring).")
            has_error = True

        # Check 2: All annotators have descriptions and valid signatures
        for func_name, func_info in mod_info.functions.items():
            full_name = f"{module_name}:{func_name}"
            # Check description
            if not func_info.get("description"):
                self._log_error(f"Annotator '{full_name}' is missing a description.")
                has_error = True
            # Check signature for type hints
            try:
                sig = inspect.signature(func_info["function"], eval_str=True)
                for param in sig.parameters.values():
                    if param.annotation is inspect.Parameter.empty:
                        self._log_error(f"Parameter '{param.name}' in '{full_name}' is missing a type hint.")
                        has_error = True
                    # Check that Output annotations have a description
                    if (
                        isinstance(param.default, BaseOutput)
                        and not param.default.description
                        and func_info["type"] is registry.Annotator.annotator
                    ):
                        self._log_error(f"Output '{param.default.name}' in '{full_name}' is missing a description.")
                        has_error = True

            except (TypeError, NameError) as e:
                self._log_error(f"Could not inspect signature for '{full_name}'. Possible broken type hint? Error: {e}")
                has_error = True

        if not has_error:
            self._log_success("Module passed all checks.")

    def _log_error(self, message: str) -> None:
        self.failed_checks += 1
        console.print(f"  [red]✖ ERROR:[/red] {message}")

    def _log_success(self, message: str) -> None:
        self.passed_checks += 1
        console.print(f"  [green]✔ OK:[/green] {message}")
