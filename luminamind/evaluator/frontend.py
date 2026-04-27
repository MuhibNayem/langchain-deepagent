"""FrontendEvaluator - visual quality scoring for frontend design artifacts.

GE-05: Frontend design evaluator produces actionable critique with visual quality scoring.
Covers: layout, typography, color, spacing, responsiveness.

DesignCriteria weights for overall scoring:
- layout: 0.25
- typography: 0.20
- color: 0.15
- spacing: 0.20
- responsiveness: 0.20
"""
from __future__ import annotations

import re
from typing import Any

from luminamind.evaluator.criteria import DesignCriteria


class FrontendEvaluator(DesignCriteria):
    """Frontend design evaluator per GE-05.

    Produces specific, actionable critique with visual quality scoring.
    Covers: layout, typography, color, spacing, responsiveness.

    Attributes:
        domain: Always "design" for frontend evaluation
        tolerance: Calibration threshold for visual comparisons (default 0.85)
    """

    domain = "design"

    def __init__(self, tolerance: float = 0.85):
        """Initialize FrontendEvaluator.

        Args:
            tolerance: Calibration threshold for visual comparisons (0-1).
                       Higher values mean stricter matching.
        """
        self.tolerance = tolerance

    def evaluate(self, artifact: Any) -> dict:
        """Evaluate frontend design artifact.

        Args:
            artifact: HTML/CSS/JS content or screenshot description

        Returns dict with:
            - visual_quality_score: float (0-100)
            - layout_score: float
            - typography_score: float
            - color_score: float
            - spacing_score: float
            - responsiveness_score: float
            - issues: list[dict]  # {type, location, description, severity, current_value, suggested_fix}
            - strengths: list[str]
            - recommendations: list[dict]  # {action, priority, expected_impact, related_issue}
        """
        scores = {
            "layout": self._score_layout(artifact),
            "typography": self._score_typography(artifact),
            "color": self._score_color(artifact),
            "spacing": self._score_spacing(artifact),
            "responsiveness": self._score_responsiveness(artifact),
        }

        visual_quality_score = (
            scores["layout"] * 0.25 +
            scores["typography"] * 0.20 +
            scores["color"] * 0.15 +
            scores["spacing"] * 0.20 +
            scores["responsiveness"] * 0.20
        )

        return {
            "visual_quality_score": visual_quality_score,
            "layout_score": scores["layout"],
            "typography_score": scores["typography"],
            "color_score": scores["color"],
            "spacing_score": scores["spacing"],
            "responsiveness_score": scores["responsiveness"],
            "issues": self._find_issues(artifact, scores),
            "strengths": self._find_strengths(artifact, scores),
            "recommendations": self._generate_recommendations(scores),
        }

    def _score_layout(self, artifact: Any) -> float:
        """Score layout quality (0-100).

        Checks for:
        - Semantic structure (header, main, footer, nav)
        - Container elements
        - Grid/flex usage
        - Proper nesting
        """
        artifact_str = str(artifact)
        score = 70.0  # Base score

        # Check for semantic HTML structure
        semantic_tags = ["header", "footer", "nav", "main", "section", "article", "aside"]
        found_semantic = sum(1 for tag in semantic_tags if f"<{tag}" in artifact_str.lower())
        if found_semantic >= 3:
            score += 15
        elif found_semantic >= 1:
            score += 8
        else:
            score -= 10

        # Check for container elements
        containers = ["div", "span", "container", "wrapper", "grid"]
        found_containers = sum(1 for c in containers if f"<{c}" in artifact_str.lower())
        if found_containers >= 3:
            score += 10
        elif found_containers >= 1:
            score += 5

        # Check for layout utilities (flex/grid)
        if "flex" in artifact_str.lower() or "grid" in artifact_str.lower():
            score += 10

        # Check for proper closing tags (balanced HTML)
        open_tags = len(re.findall(r"<[a-z]+[^>]*>", artifact_str.lower()))
        close_tags = len(re.findall(r"</[a-z]+>", artifact_str.lower()))
        if open_tags > 0 and close_tags > 0:
            tag_ratio = min(open_tags, close_tags) / max(open_tags, close_tags)
            if tag_ratio < 0.7:
                score -= 15
            elif tag_ratio >= 0.9:
                score += 5

        # Check for inline styles that might indicate poor structure
        inline_styles = len(re.findall(r'style=["\']', artifact_str))
        if inline_styles > 5:
            score -= 10

        return max(0.0, min(100.0, score))

    def _score_typography(self, artifact: Any) -> float:
        """Score typography quality (0-100).

        Checks for:
        - Font family specification
        - Font size appropriateness (not too small)
        - Line height
        - Text hierarchy (headings)
        """
        artifact_str = str(artifact)
        score = 65.0  # Base score

        # Check for font-family
        if "font-family" in artifact_str.lower():
            score += 15
        elif any(fw in artifact_str.lower() for fw in ["arial", "times", "helvetica", "sans-serif", "serif"]):
            score += 8

        # Check for font-size ( penalize too small)
        font_sizes = re.findall(r"font-size:\s*(\d+)px", artifact_str.lower())
        if font_sizes:
            sizes = [int(fs) for fs in font_sizes]
            if any(s < 12 for s in sizes):
                score -= 15
            if any(s >= 14 for s in sizes):
                score += 5

        # Check for line-height
        if "line-height" in artifact_str.lower():
            score += 10

        # Check for heading hierarchy
        headings = re.findall(r"<h([1-6])", artifact_str.lower())
        if headings:
            h_levels = [int(h) for h in headings]
            # Check for proper hierarchy (h1 before h2, etc.)
            if sorted(h_levels) == h_levels and len(set(h_levels)) > 1:
                score += 10
            elif len(headings) >= 2:
                score += 5

        # Check for text containers
        text_tags = ["p", "span", "div", "text"]
        has_text = any(f"<{t}" in artifact_str.lower() for t in text_tags)
        if has_text:
            score += 5

        # Penalize very small font-size in style attributes
        tiny_fonts = len(re.findall(r'font-size:\s*\d+px', artifact_str))
        if tiny_fonts > 0:
            score -= tiny_fonts * 5

        return max(0.0, min(100.0, score))

    def _score_color(self, artifact: Any) -> float:
        """Score color usage (0-100).

        Checks for:
        - Color palette consistency
        - Contrast considerations
        - Background/text color pairing
        - Color values (not just color names)
        """
        artifact_str = str(artifact)
        score = 60.0  # Base score

        # Check for hex color values
        hex_colors = len(re.findall(r"#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})", artifact_str))
        if hex_colors >= 3:
            score += 15
        elif hex_colors >= 1:
            score += 8

        # Check for rgb/rgba
        rgb_colors = len(re.findall(r"rgb\(", artifact_str.lower()))
        if rgb_colors >= 2:
            score += 10

        # Check for color names (less specific)
        color_names = ["red", "blue", "green", "white", "black", "gray", "grey", "yellow", "purple"]
        found_colors = sum(1 for c in color_names if f" {c}" in artifact_str.lower() or f",{c}" in artifact_str.lower())
        if found_colors >= 3:
            score += 5  # Some color usage

        # Check for background-color
        if "background-color" in artifact_str.lower() or "background:" in artifact_str.lower():
            score += 10

        # Check for contrast indicators (hard to detect automatically, but look for related attributes)
        contrast_keywords = ["contrast", "opacity", "alpha"]
        if any(kw in artifact_str.lower() for kw in contrast_keywords):
            score += 5

        # Penalize if only color names used without specific values
        if hex_colors == 0 and rgb_colors == 0 and found_colors > 0:
            score -= 5

        return max(0.0, min(100.0, score))

    def _score_spacing(self, artifact: Any) -> float:
        """Score spacing and alignment (0-100).

        Checks for:
        - Padding/margin usage
        - Consistent spacing values
        - Alignment indicators
        """
        artifact_str = str(artifact)
        score = 60.0  # Base score

        # Check for padding
        padding_count = len(re.findall(r"padding", artifact_str.lower()))
        if padding_count >= 3:
            score += 15
        elif padding_count >= 1:
            score += 8

        # Check for margin
        margin_count = len(re.findall(r"margin", artifact_str.lower()))
        if margin_count >= 2:
            score += 10
        elif margin_count >= 1:
            score += 5

        # Check for specific spacing values (16px, 8px, etc.)
        spacing_values = re.findall(r"(?:padding|margin|gap):\s*(\d+)px", artifact_str.lower())
        if spacing_values:
            values = [int(sv) for sv in spacing_values]
            # Check for consistent spacing (multiples of 4 or 8)
            if len(values) >= 2:
                # Good: consistent spacing like 8, 16, 24
                if all(v % 4 == 0 for v in values):
                    score += 10
            # Penalize very small spacing
            if any(v < 4 and v > 0 for v in values):
                score -= 10

        # Check for gap in flex/grid
        if "gap:" in artifact_str.lower() or "gap-" in artifact_str.lower():
            score += 10

        # Check for alignment
        align_keywords = ["align-items", "align-content", "justify-content", "text-align"]
        if any(ak in artifact_str.lower() for ak in align_keywords):
            score += 8

        # Penalize zero padding/margin on interactive elements
        if "<button" in artifact_str.lower() or "<input" in artifact_str.lower():
            if "padding: 0" in artifact_str.lower() or "padding:0" in artifact_str.lower():
                score -= 15

        return max(0.0, min(100.0, score))

    def _score_responsiveness(self, artifact: Any) -> float:
        """Score responsiveness (0-100).

        Checks for:
        - Media queries
        - Viewport meta tag
        - Relative units (%, em, rem)
        - Max-width constraints
        """
        artifact_str = str(artifact)
        score = 55.0  # Base score

        # Check for viewport meta
        if 'viewport' in artifact_str.lower() and 'content=' in artifact_str.lower():
            score += 20

        # Check for media queries
        media_queries = len(re.findall(r"@media", artifact_str.lower()))
        if media_queries >= 2:
            score += 15
        elif media_queries >= 1:
            score += 8

        # Check for relative units
        relative_units = re.findall(r"(\d+(?:\.\d+)?)(rem|em|%|vw|vh)", artifact_str.lower())
        if len(relative_units) >= 3:
            score += 15
        elif len(relative_units) >= 1:
            score += 8

        # Check for max-width
        if "max-width" in artifact_str.lower():
            score += 10

        # Check for flex-wrap
        if "flex-wrap" in artifact_str.lower():
            score += 8

        # Check for mobile-specific patterns
        mobile_patterns = ["mobile", "touch", "hover"]
        if any(p in artifact_str.lower() for p in mobile_patterns):
            score += 5

        # Penalize fixed pixel values for key dimensions
        fixed_widths = len(re.findall(r"(?:width|height):\s*\d+px", artifact_str.lower()))
        if fixed_widths > 5:
            score -= 10

        return max(0.0, min(100.0, score))

    def _find_issues(self, artifact: Any, scores: dict) -> list[dict]:
        """Generate specific, actionable issues.

        Returns list of:
        {
            "type": str,           # e.g., "spacing", "typography", "color"
            "location": str,       # e.g., "button.btn-primary at line 42"
            "description": str,    # e.g., "Insufficient padding"
            "severity": str,       # "critical" | "major" | "minor"
            "current_value": str, # e.g., "padding: 4px"
            "suggested_fix": str,  # e.g., "padding: 16px"
        }
        """
        issues = []
        artifact_str = str(artifact)

        # Layout issues
        if scores["layout"] < 60:
            # Check for missing semantic structure
            semantic_tags = ["header", "footer", "nav", "main"]
            missing = [t for t in semantic_tags if f"<{t}" not in artifact_str.lower()]
            if missing:
                issues.append({
                    "type": "layout",
                    "location": "HTML structure",
                    "description": f"Missing semantic elements: {', '.join(missing)}",
                    "severity": "major",
                    "current_value": "No semantic HTML5 elements",
                    "suggested_fix": f"Add <{missing[0]}> element(s) for proper document structure"
                })

            # Check for unbalanced tags
            open_count = len(re.findall(r"<[a-z]+[^>]*>", artifact_str.lower()))
            close_count = len(re.findall(r"</[a-z]+>", artifact_str.lower()))
            if open_count > 0 and close_count > 0 and (open_count / close_count) > 1.2:
                issues.append({
                    "type": "layout",
                    "location": "HTML tags",
                    "description": "Unbalanced HTML tags detected",
                    "severity": "critical",
                    "current_value": f"{open_count} open tags, {close_count} close tags",
                    "suggested_fix": "Ensure all open tags have corresponding closing tags"
                })

        # Typography issues
        if scores["typography"] < 60:
            # Check for small font sizes
            small_fonts = re.findall(r'font-size:\s*(\d+)px', artifact_str.lower())
            if small_fonts:
                tiny = [int(f) for f in small_fonts if int(f) < 12]
                if tiny:
                    issues.append({
                        "type": "typography",
                        "location": "CSS font-size declarations",
                        "description": f"Font size(s) too small: {tiny}px (minimum recommended: 12px)",
                        "severity": "critical",
                        "current_value": f"font-size: {tiny[0]}px",
                        "suggested_fix": "Increase font-size to at least 12px (14-16px recommended for body text)"
                    })

            # Check for missing heading hierarchy
            headings = re.findall(r"<h([1-6])", artifact_str.lower())
            if headings and len(headings) > 1:
                h_levels = [int(h) for h in headings]
                if sorted(h_levels) != h_levels:
                    issues.append({
                        "type": "typography",
                        "location": "Heading elements",
                        "description": "Heading hierarchy is not properly ordered",
                        "severity": "major",
                        "current_value": f"Found headings: h{', '.join(str(h) for h in h_levels)}",
                        "suggested_fix": "Reorder headings to follow logical hierarchy (h1 → h2 → h3)"
                    })

        # Spacing issues
        if scores["spacing"] < 60:
            # Check for missing padding on buttons/inputs
            if "<button" in artifact_str.lower() or "<input" in artifact_str.lower():
                # Look for padding: 0 or very small padding on buttons
                button_styles = re.findall(r"button[^}]*padding:\s*(\d+)px", artifact_str.lower())
                if button_styles:
                    padding_values = [int(p) for p in button_styles]
                    if any(p < 8 for p in padding_values):
                        issues.append({
                            "type": "spacing",
                            "location": "button element",
                            "description": "Button padding is too small (minimum 44px touch target)",
                            "severity": "critical",
                            "current_value": f"padding: {min(padding_values)}px",
                            "suggested_fix": "Increase padding to at least 12px (16px preferred)"
                        })
                elif "padding" not in artifact_str.lower():
                    issues.append({
                        "type": "spacing",
                        "location": "button element",
                        "description": "Button missing explicit padding",
                        "severity": "major",
                        "current_value": "No padding declaration",
                        "suggested_fix": "Add padding: 12px 16px for proper button sizing"
                    })

            # Check for inconsistent spacing values
            spacing_values = re.findall(r"(?:padding|margin|gap):\s*(\d+)px", artifact_str.lower())
            if spacing_values:
                values = [int(sv) for sv in spacing_values]
                # Check for inconsistent values (not multiples of 4)
                inconsistent = [v for v in values if v % 4 != 0]
                if len(inconsistent) > 2:
                    issues.append({
                        "type": "spacing",
                        "location": "CSS spacing declarations",
                        "description": "Inconsistent spacing values detected",
                        "severity": "minor",
                        "current_value": f"Mixed spacing: {spacing_values[:5]}",
                        "suggested_fix": "Use consistent spacing scale: 4px, 8px, 12px, 16px, 24px, 32px"
                    })

        # Responsiveness issues
        if scores["responsiveness"] < 60:
            if 'viewport' not in artifact_str.lower():
                issues.append({
                    "type": "responsiveness",
                    "location": "<head> section",
                    "description": "Missing viewport meta tag for mobile responsiveness",
                    "severity": "critical",
                    "current_value": "No viewport meta tag",
                    "suggested_fix": "Add <meta name='viewport' content='width=device-width, initial-scale=1'>"
                })

            # Check for media queries
            if "@media" not in artifact_str.lower():
                issues.append({
                    "type": "responsiveness",
                    "location": "CSS",
                    "description": "No media queries found - layout may not adapt to different screen sizes",
                    "severity": "major",
                    "current_value": "No @media rules",
                    "suggested_fix": "Add @media queries for at least mobile (max-width: 768px) and tablet breakpoints"
                })

            # Check for fixed widths on containers
            fixed_widths = re.findall(r"width:\s*(\d+)px", artifact_str.lower())
            if fixed_widths:
                large_fixed = [int(w) for w in fixed_widths if w > 1200]
                if large_fixed:
                    issues.append({
                        "type": "responsiveness",
                        "location": "Container elements",
                        "description": "Fixed widths may prevent proper scaling on smaller screens",
                        "severity": "major",
                        "current_value": f"width: {large_fixed[0]}px",
                        "suggested_fix": "Use max-width or percentage-based widths instead"
                    })

        return issues

    def _find_strengths(self, artifact: Any, scores: dict) -> list[str]:
        """Find strengths in the design."""
        strengths = []
        artifact_str = str(artifact)

        if scores["layout"] >= 75:
            if any(tag in artifact_str.lower() for tag in ["<header", "<main", "<footer", "<nav"]):
                strengths.append("Uses semantic HTML5 structure")

        if scores["layout"] >= 70:
            if "flex" in artifact_str.lower() or "grid" in artifact_str.lower():
                strengths.append("Modern CSS layout techniques (flex/grid)")

        if scores["typography"] >= 75:
            if "font-family" in artifact_str.lower():
                strengths.append("Custom font-family specified")
            if re.findall(r"<h[1-3]", artifact_str.lower()):
                strengths.append("Proper heading hierarchy established")

        if scores["color"] >= 70:
            if re.findall(r"#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})", artifact_str):
                strengths.append("Uses hex color values for consistency")

        if scores["spacing"] >= 70:
            if "gap:" in artifact_str.lower() or "gap-" in artifact_str.lower():
                strengths.append("Uses gap property for consistent spacing")

        if scores["responsiveness"] >= 70:
            if "@media" in artifact_str.lower():
                strengths.append("Implements responsive breakpoints")
            if re.findall(r"(rem|em|%)", artifact_str.lower()):
                strengths.append("Uses relative units for scalability")

        return strengths

    def _generate_recommendations(self, scores: dict) -> list[dict]:
        """Generate actionable recommendations.

        Returns list of:
        {
            "action": str,            # e.g., "Change .btn-primary padding to 16px"
            "priority": str,          # "high" | "medium" | "low"
            "expected_impact": str,   # e.g., "Improves click target to 44px min"
            "related_issue": str,     # reference to issue type
        }
        """
        recommendations = []

        # Layout recommendations
        if scores["layout"] < 70:
            recommendations.append({
                "action": "Add semantic HTML5 elements (header, main, footer, nav)",
                "priority": "high",
                "expected_impact": "Improves accessibility and SEO",
                "related_issue": "layout"
            })

        # Typography recommendations
        if scores["typography"] < 70:
            recommendations.append({
                "action": "Set base font-size to at least 16px and use rem units",
                "priority": "high",
                "expected_impact": "Improves readability and mobile experience",
                "related_issue": "typography"
            })
            recommendations.append({
                "action": "Establish clear heading hierarchy (h1 → h2 → h3)",
                "priority": "medium",
                "expected_impact": "Improves content structure and accessibility",
                "related_issue": "typography"
            })

        # Color recommendations
        if scores["color"] < 70:
            recommendations.append({
                "action": "Define a consistent color palette with hex values",
                "priority": "medium",
                "expected_impact": "Improves visual consistency and brand identity",
                "related_issue": "color"
            })

        # Spacing recommendations
        if scores["spacing"] < 70:
            recommendations.append({
                "action": "Add consistent spacing scale (4px base unit)",
                "priority": "high",
                "expected_impact": "Improves visual rhythm and layout balance",
                "related_issue": "spacing"
            })
            recommendations.append({
                "action": "Ensure interactive elements have minimum 44px touch targets",
                "priority": "high",
                "expected_impact": "Meets mobile accessibility requirements",
                "related_issue": "spacing"
            })

        # Responsiveness recommendations
        if scores["responsiveness"] < 70:
            recommendations.append({
                "action": "Add viewport meta tag and responsive breakpoints",
                "priority": "high",
                "expected_impact": "Enables proper mobile rendering",
                "related_issue": "responsiveness"
            })
            recommendations.append({
                "action": "Replace fixed pixel widths with relative units (%, rem, em)",
                "priority": "medium",
                "expected_impact": "Improves fluid responsiveness across screen sizes",
                "related_issue": "responsiveness"
            })

        return recommendations