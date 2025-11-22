import sympy as sp
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

# Reuse the robust parser logic
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)


@dataclass
class PointFeature:
    x: float
    y: float
    label: str
    feature_type: str  # 'intercept', 'stationary', 'inflection', 'endpoint'
    marker_style: str  # 'filled', 'hollow', 'cross'
    priority: int = 0


class MathAnalyser:
    def __init__(self, expr_str: str):
        self.x = sp.symbols('x')
        self.valid = False
        self.expr = None
        self.error_msg = ""
        self.f_lambda = None

        if not expr_str or not expr_str.strip():
            return

        clean_str = expr_str.strip()
        if clean_str.lower().startswith("y") and "=" in clean_str:
            clean_str = clean_str.split("=", 1)[1]

        transformations = (standard_transformations +
                           (implicit_multiplication_application, convert_xor))

        try:
            self.expr = parse_expr(clean_str, transformations=transformations)
            self.f_lambda = sp.lambdify(self.x, self.expr, modules=['math'])
            self.valid = True
        except Exception as e:
            self.error_msg = str(e)
            self.valid = False

    def evaluate(self, x_val: float) -> Optional[float]:
        if not self.valid or self.f_lambda is None: return None
        try:
            val = self.f_lambda(x_val)
            if math.isfinite(val):
                return float(val)
        except:
            pass
        return None

    def _format_number(self, val, exact: bool) -> str:
        """
        Formats a number. If exact=True, tries to convert floats to rationals/integers
        (e.g. -5.0 -> -5, 3.25 -> 13/4) before LaTeX conversion.
        """
        if exact:
            try:
                # Attempt to simplify float to exact rational/integer
                # tolerance=1e-8 ensures we don't weirdly convert 3.14159 to a huge fraction
                # rational=True forces conversion if close
                val_simplified = sp.nsimplify(val, tolerance=1e-8, rational=True)
                return sp.latex(val_simplified)
            except:
                return sp.latex(val)
        else:
            try:
                f_val = float(val)
                if abs(f_val - round(f_val)) < 1e-9:
                    return str(int(round(f_val)))
                return f"{f_val:.2f}"
            except:
                return str(val)

    def _make_label(self, x_val, y_val, exact: bool) -> str:
        x_str = self._format_number(x_val, exact)
        y_str = self._format_number(y_val, exact)
        return f"({x_str}, {y_str})"

    def _solve_in_domain(self, equation, domain_min, domain_max):
        """
        Robust solver that finds all real roots within a numeric window.
        Handles periodic functions (sin, cos) correctly using solveset.
        """
        results = []
        try:
            # 1. Try standard solve first (faster for simple polynomials)
            roots = sp.solve(equation, self.x)

            # If solve returns generic solutions or misses periodic ones, we might need solveset
            # But specific check: if we found roots, are they exhaustive?
            # For polynomials, yes. For sin(x), no.

            # Let's verify with solveset for robustness on viewing window
            domain_interval = sp.Interval(domain_min, domain_max)
            solution_set = sp.solveset(equation, self.x, domain=sp.S.Reals)

            # Intersect with our viewing window
            intersection = sp.Intersection(solution_set, domain_interval)

            # Extract values
            if isinstance(intersection, sp.FiniteSet):
                for arg in intersection:
                    results.append(arg)
            elif isinstance(intersection, sp.Union):
                for subset in intersection.args:
                    if isinstance(subset, sp.FiniteSet):
                        for arg in subset:
                            results.append(arg)

            # Fallback: if solveset failed or returned ConditionSet, use the basic `roots`
            # and filter manually (though roots might miss periodic ones)
            if not results and roots:
                # Filter manual roots
                for r in roots:
                    try:
                        r_float = float(r)
                        if domain_min - 1e-9 <= r_float <= domain_max + 1e-9:
                            results.append(r)
                    except:
                        pass

        except Exception:
            # Last resort fallback
            pass

        # Deduplicate based on float value to avoid mixing 0 and 0.0
        unique_results = []
        seen_floats = set()
        for r in results:
            try:
                r_f = float(r)
                is_new = True
                for seen in seen_floats:
                    if abs(r_f - seen) < 1e-7:
                        is_new = False
                        break
                if is_new:
                    seen_floats.add(r_f)
                    unique_results.append(r)
            except:
                pass

        return unique_results

    def get_features(self,
                     domain: Tuple[float, float],
                     show_y_intercept: bool = False,
                     show_x_intercepts: bool = False,
                     show_stationary: bool = False,
                     show_inflection: bool = False,
                     show_endpoints: bool = False,
                     endpoint_types: Tuple[str, str] = ("filled", "filled"),
                     exact_values: bool = True) -> List[PointFeature]:

        if not self.valid:
            return []

        features = []
        min_x, max_x = domain
        epsilon = 1e-9

        # --- 1. Y-Intercept (x = 0) ---
        if show_y_intercept and (min_x - epsilon <= 0 <= max_x + epsilon):
            try:
                y_sym = self.expr.subs(self.x, 0)
                if y_sym.is_real:
                    label = self._make_label(0, y_sym, exact_values)
                    features.append(PointFeature(0.0, float(y_sym), label, 'intercept', 'filled'))
            except:
                pass

        # --- 2. X-Intercepts (y = 0) ---
        if show_x_intercepts:
            roots = self._solve_in_domain(self.expr, min_x, max_x)
            for r in roots:
                label = self._make_label(r, 0, exact_values)
                features.append(PointFeature(float(r), 0.0, label, 'intercept', 'filled'))

        # --- 3. Stationary Points (dy/dx = 0) ---
        if show_stationary:
            try:
                deriv = sp.diff(self.expr, self.x)
                crit_points = self._solve_in_domain(deriv, min_x, max_x)
                for cp in crit_points:
                    y_val = self.expr.subs(self.x, cp)
                    label = self._make_label(cp, y_val, exact_values)
                    features.append(PointFeature(float(cp), float(y_val), label, 'stationary', 'filled'))
            except:
                pass

        # --- 4. Inflection Points (d2y/dx2 = 0) ---
        if show_inflection:
            try:
                d2 = sp.diff(self.expr, self.x, 2)
                inf_points = self._solve_in_domain(d2, min_x, max_x)
                for ip in inf_points:
                    y_val = self.expr.subs(self.x, ip)
                    label = self._make_label(ip, y_val, exact_values)
                    features.append(PointFeature(float(ip), float(y_val), label, 'inflection', 'filled'))
            except:
                pass

        # --- 5. Endpoints ---
        if show_endpoints:
            # Start
            try:
                # nsimplify min_x for symbolic substitution (better precision)
                # e.g. passes -5 instead of -5.000000
                x_start_sym = sp.nsimplify(min_x, tolerance=1e-8, rational=True)
                y_start = self.expr.subs(self.x, x_start_sym)

                if y_start.is_real:
                    label = self._make_label(x_start_sym, y_start, exact_values)
                    features.append(PointFeature(min_x, float(y_start), label, 'endpoint', endpoint_types[0]))
            except:
                pass

            # End
            try:
                x_end_sym = sp.nsimplify(max_x, tolerance=1e-8, rational=True)
                y_end = self.expr.subs(self.x, x_end_sym)

                if y_end.is_real:
                    label = self._make_label(x_end_sym, y_end, exact_values)
                    features.append(PointFeature(max_x, float(y_end), label, 'endpoint', endpoint_types[1]))
            except:
                pass

        return features