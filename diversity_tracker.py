"""
The Last Shelter — Diversity Tracker
Scans all existing projects to build a usage map and generate
diversity constraints for story generation prompts.
"""
import json
from pathlib import Path
from collections import Counter

PROJECTS_DIR = Path(__file__).parent / "projects"

# Approved locations from STORY_DNA — worldwide, organized by continent
ALL_LOCATIONS = [
    # North America
    "Yukon, Canadá", "Alaska, USA", "Montana, USA", "British Columbia, Canadá",
    "Minnesota, USA", "Maine, USA", "Colorado Rockies, USA", "Quebec, Canadá",
    "Northwest Territories, Canadá", "New Brunswick, Canadá",
    # Europe
    "Norte de Noruega", "Suecia", "Laponia, Finlandia", "Islandia",
    "Escocia", "Rumanía", "Alpes Suizos", "Noruega Sur",
    "Irlanda", "Pirineos, España/Francia", "Cárpatos, Ucrania", "Alpes Italianos",
    # Asia & Siberia
    "Siberia, Rusia", "Japón", "Mongolia", "Kazajistán",
    "Corea del Sur", "Kamchatka, Rusia",
    # South America
    "Patagonia, Argentina", "Patagonia, Chile", "Andes, Bolivia", "Sur de Brasil",
    # Oceania
    "Nueva Zelanda", "Tasmania, Australia",
    # Africa
    "Atlas, Marruecos", "Highlands, Etiopía",
]

# All 10 viral archetypes from STORY_DNA
ALL_ARCHETYPES = [
    "The Promise", "The Last Chance", "The Aftermath", "The Inherited Burden",
    "The Wrong Season", "The Solitary Vigil", "The Community Build",
    "The Obsession", "The Silent Witness", "The Failure"
]

# All episode types
ALL_EPISODE_TYPES = [
    "build", "rescue", "restore", "survive", "full_build",
    "critical_system", "underground", "cabin_life"
]

# Common companion breeds to rotate
ALL_COMPANION_BREEDS = [
    "Husky", "German Shepherd", "Malamute", "Border Collie", "Labrador",
    "Norwegian Elkhound", "Bernese Mountain Dog", "Akita", "Australian Shepherd",
    "Karelian Bear Dog", "Samoyed", "Siberian Laika"
]


def scan_existing_projects():
    """
    Scan all existing projects and build usage maps.
    
    Returns:
        Dict with counters for names, locations, archetypes, types, companions
    """
    usage = {
        "character_names": [],
        "character_origins": [],
        "character_professions": [],
        "locations_region": [],
        "locations_specific": [],
        "archetypes": [],
        "episode_types": [],
        "companion_names": [],
        "companion_breeds": [],
        "ages": [],
        "total_episodes": 0
    }
    
    if not PROJECTS_DIR.exists():
        return usage
    
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        
        story_path = project_dir / "story.json"
        if not story_path.exists():
            continue
        
        try:
            with open(story_path) as f:
                story = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue
        
        usage["total_episodes"] += 1
        
        # Character info
        char = story.get("character", {})
        if char.get("name"):
            usage["character_names"].append(char["name"])
        if char.get("origin"):
            usage["character_origins"].append(char["origin"])
        if char.get("profession"):
            usage["character_professions"].append(char["profession"])
        if char.get("age"):
            usage["ages"].append(char["age"])
        
        # Companion
        companion = char.get("companion", {})
        if companion.get("name"):
            usage["companion_names"].append(companion["name"])
        if companion.get("breed"):
            usage["companion_breeds"].append(companion["breed"])
        
        # Location
        loc = story.get("location", {})
        if loc.get("name"):
            usage["locations_specific"].append(loc["name"])
            # Extract region (first part before comma or known region)
            for region in ALL_LOCATIONS:
                region_key = region.split(",")[0].lower()
                if region_key in loc["name"].lower():
                    usage["locations_region"].append(region)
                    break
        
        # Archetype
        if story.get("archetype"):
            usage["archetypes"].append(story["archetype"])
        
        # Episode type
        if story.get("episode_type"):
            usage["episode_types"].append(story["episode_type"])
    
    return usage


def get_unused_or_least_used(used_list, all_options, top_n=3):
    """Get the least-used options from a list."""
    counts = Counter(used_list)
    # Items never used
    unused = [opt for opt in all_options if opt not in counts]
    if unused:
        return unused[:top_n]
    # Least used
    sorted_opts = sorted(all_options, key=lambda x: counts.get(x, 0))
    return sorted_opts[:top_n]


def get_diversity_context():
    """
    Generate a diversity constraint text block to inject into the story prompt.
    
    Returns:
        String with AVOID and PREFER sections for the prompt
    """
    usage = scan_existing_projects()
    
    if usage["total_episodes"] == 0:
        return ""  # No history yet — no constraints needed
    
    lines = []
    lines.append("---")
    lines.append("## DIVERSITY CONSTRAINTS (from episode memory)")
    lines.append(f"Total episodes generated so far: {usage['total_episodes']}")
    lines.append("")
    
    # AVOID section
    lines.append("### ❌ AVOID (already used — DO NOT repeat)")
    
    if usage["character_names"]:
        lines.append(f"- Names already used: {', '.join(usage['character_names'])}")
    if usage["companion_names"]:
        lines.append(f"- Companion names already used: {', '.join(usage['companion_names'])}")
    if usage["locations_specific"]:
        lines.append(f"- Specific locations already used: {', '.join(usage['locations_specific'])}")
    if usage["character_origins"]:
        lines.append(f"- Character origins already used: {', '.join(usage['character_origins'])}")
    
    lines.append("")
    
    # PREFER section
    lines.append("### ✅ PREFER (least used — prioritize these)")
    
    # Recommend least-used archetypes
    rec_archetypes = get_unused_or_least_used(usage["archetypes"], ALL_ARCHETYPES)
    if rec_archetypes:
        lines.append(f"- Preferred archetypes (least used): {', '.join(rec_archetypes)}")
    
    # Recommend least-used locations
    rec_locations = get_unused_or_least_used(usage["locations_region"], ALL_LOCATIONS)
    if rec_locations:
        lines.append(f"- Preferred locations (least used): {', '.join(rec_locations)}")
    
    # Recommend least-used companion breeds
    rec_breeds = get_unused_or_least_used(usage["companion_breeds"], ALL_COMPANION_BREEDS)
    if rec_breeds:
        lines.append(f"- Preferred companion breeds (least used): {', '.join(rec_breeds)}")
    
    # Recommend least-used episode types
    rec_types = get_unused_or_least_used(usage["episode_types"], ALL_EPISODE_TYPES)
    if rec_types:
        lines.append(f"- Least-used episode types: {', '.join(rec_types)}")
    
    # Age diversity
    if usage["ages"]:
        avg_age = sum(usage["ages"]) / len(usage["ages"])
        if avg_age > 45:
            lines.append("- Age: Previous characters skew older. Consider a YOUNGER character (18-35).")
        elif avg_age < 35:
            lines.append("- Age: Previous characters skew younger. Consider an OLDER character (50-65).")
    
    lines.append("")
    lines.append("Use different names, origins, locations, breeds, and archetypes from previous episodes.")
    lines.append("Violating AVOID constraints will result in rejection.")
    lines.append("---")
    
    return "\n".join(lines)


def get_recommendations():
    """
    Get structured recommendations for UI display.
    
    Returns:
        Dict with recommended archetypes, locations, types, etc.
    """
    usage = scan_existing_projects()
    
    return {
        "total_episodes": usage["total_episodes"],
        "used": {
            "names": usage["character_names"],
            "locations": usage["locations_specific"],
            "archetypes": Counter(usage["archetypes"]).most_common(),
            "episode_types": Counter(usage["episode_types"]).most_common(),
            "companion_breeds": Counter(usage["companion_breeds"]).most_common(),
        },
        "recommended": {
            "archetypes": get_unused_or_least_used(usage["archetypes"], ALL_ARCHETYPES, 5),
            "locations": get_unused_or_least_used(usage["locations_region"], ALL_LOCATIONS, 5),
            "episode_types": get_unused_or_least_used(usage["episode_types"], ALL_EPISODE_TYPES, 5),
            "companion_breeds": get_unused_or_least_used(usage["companion_breeds"], ALL_COMPANION_BREEDS, 5),
        }
    }
