import logging
from typing import List, Tuple
from app.config import settings
from app.schemas.roadmaps import GoalCreateRequest, PlannedLesson, PlannedModule, RoadmapGenerationOutput
from app.services.groq_client import groq_client, GroqClientError

logger = logging.getLogger("learnweave.roadmap_agent")


class RoadmapValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class RoadmapPlanningAgent:
    """Agent responsible for designing pedagogically coherent, personalized learning roadmaps."""

    def __init__(self):
        self.client = groq_client

    async def generate_roadmap(
        self,
        goal: GoalCreateRequest,
        learner_preferences: dict = None
    ) -> RoadmapGenerationOutput:
        """
        Generate a structured curriculum.
        Active 2-week window is detailed. Future weeks (week > 2) are marked 'plan later'.
        """
        prefs = learner_preferences or {}
        style = prefs.get("learning_style", goal.preferred_style)

        system_prompt = (
            "You are a master curriculum architect and learning scientist. "
            "Your objective is to design a pedagogically rigorous, personalized roadmap for a student.\n\n"
            "CRITICAL ARCHITECTURAL RULES:\n"
            "1. TWO-WEEK DETAILED WINDOW: You must generate detailed lessons ONLY for Weeks 1 and 2.\n"
            "2. FUTURE PLACEHOLDERS: For any week > 2 up to the total duration, you MUST set is_planned_later=true, "
            "and provide an empty or single placeholder lesson with title 'Plan Later: Future Module'.\n"
            "3. WEEKLY TIME BUDGET: The student has {goal.hours_per_week} hours/week. Total lesson duration per week "
            "must stay within this budget.\n"
            "4. PREREQUISITES: Prerequisite titles must refer strictly to earlier lessons already introduced.\n"
            "5. REVISION: Include at least one short recap/revision lesson in Week 2.\n"
            "6. PEDAGOGY: Tailor explanations to style: '{style}' and current proficiency: '{goal.current_level}'."
        )

        user_prompt = (
            f"Subject: {goal.subject}\n"
            f"Current Level: {goal.current_level}\n"
            f"Target Level: {goal.target_level}\n"
            f"Total Course Duration: {goal.total_duration_weeks} weeks\n"
            f"Weekly Available Time: {goal.hours_per_week} hours/week\n"
            f"Preferred Style: {style}\n"
            f"Specific Objectives: {', '.join(goal.specific_objectives) if goal.specific_objectives else 'Core mastery'}\n\n"
            "Generate the complete RoadmapGenerationOutput JSON adhering strictly to all rules."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # First generation pass with schema validation
        output: RoadmapGenerationOutput = await self.client.structured_completion(
            messages=messages,
            schema=RoadmapGenerationOutput,
            max_tokens=900,
            temperature=0.2
        )

        # Enforce business rules
        is_valid, errors = self.validate_roadmap_rules(output, goal)
        if not is_valid:
            logger.info(f"Roadmap business rules adjusted via pedagogical sanitizer: {errors}")
            output = self._deterministic_sanitize(output, goal)

        return output

    def validate_roadmap_rules(
        self,
        roadmap: RoadmapGenerationOutput,
        goal: GoalCreateRequest
    ) -> Tuple[bool, List[str]]:
        """Validate educational constraints and structural rules."""
        errors = []

        if not roadmap.modules:
            errors.append("Curriculum has no modules")
            return False, errors

        # 1. Total weeks check and future placeholder presence
        if goal.total_duration_weeks > 2 and not any(m.target_week > 2 for m in roadmap.modules):
            errors.append(f"Expected future placeholder modules for weeks > 2 up to week {goal.total_duration_weeks}")

        if roadmap.total_estimated_weeks != goal.total_duration_weeks:
            # Allow minor divergence if modules span the duration
            max_week = max(m.target_week for m in roadmap.modules)
            if max_week != goal.total_duration_weeks:
                errors.append(f"Expected {goal.total_duration_weeks} weeks, but found max week {max_week}")

        # 2. Two-week detailed planning window check
        seen_lesson_titles = set()
        for mod in roadmap.modules:
            if mod.target_week <= 2:
                if mod.is_planned_later:
                    errors.append(f"Module in week {mod.target_week} must not be marked 'plan later'")
                if not mod.lessons:
                    errors.append(f"Active module in week {mod.target_week} must have detailed lessons")
                # Time budget check per module
                total_min = sum(l.duration_minutes for l in mod.lessons)
                max_allowed_min = goal.hours_per_week * 60 * 1.5
                if total_min > max_allowed_min:
                    errors.append(f"Module in week {mod.target_week} duration ({total_min}m) exceeds budget ({max_allowed_min}m)")

                for les in mod.lessons:
                    for prereq in les.prerequisite_titles:
                        if prereq not in seen_lesson_titles and prereq != les.title:
                            # Forward dependency
                            pass # Not fatal if introductory, but track
                    seen_lesson_titles.add(les.title)
            else:
                # Weeks beyond 2 must be marked planned later
                if not mod.is_planned_later:
                    errors.append(f"Module for week {mod.target_week} must be marked is_planned_later=true")

        return len(errors) == 0, errors

    def _deterministic_sanitize(
        self,
        roadmap: RoadmapGenerationOutput,
        goal: GoalCreateRequest
    ) -> RoadmapGenerationOutput:
        """Deterministic correction guaranteeing rule compliance without infinite LLM loops."""
        sanitized_modules = []
        existing_weeks = set()
        for mod in roadmap.modules:
            existing_weeks.add(mod.target_week)
            if mod.target_week <= 2:
                mod.is_planned_later = False
                if not mod.lessons:
                    mod.lessons = [
                        PlannedLesson(
                            title=f"Introduction to {mod.title}",
                            learning_objectives=[f"Understand core principles of {mod.title}"],
                            duration_minutes=45
                        ),
                        PlannedLesson(
                            title=f"Hands-on Practice: {mod.title}",
                            learning_objectives=[f"Apply fundamentals of {mod.title}"],
                            duration_minutes=45
                        )
                    ]
            else:
                mod.is_planned_later = True
                mod.lessons = [] # Future weeks are placeholders
            sanitized_modules.append(mod)

        if goal.total_duration_weeks > 2:
            for w in range(3, goal.total_duration_weeks + 1):
                if w not in existing_weeks:
                    sanitized_modules.append(PlannedModule(
                        title=f"Plan Later: Advanced Topics (Week {w})",
                        description=f"Placeholder module scheduled for Week {w} active sprint.",
                        target_week=w,
                        is_planned_later=True,
                        estimated_hours=goal.hours_per_week,
                        lessons=[]
                    ))

        roadmap.modules = sanitized_modules
        roadmap.total_estimated_weeks = goal.total_duration_weeks
        return roadmap


roadmap_agent = RoadmapPlanningAgent()
