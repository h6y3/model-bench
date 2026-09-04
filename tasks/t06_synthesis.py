SOURCES = (
    "SOURCE A (release notes): omarchy-launcher 2.0 ships fuzzy search across all "
    "launcher modes. The launcher is now Wayland-only; X11 users must stay on 1.x.\n\n"
    "SOURCE B (migration guide): configuration moved to ~/.config/omarchy-launcher/. "
    "Old configs are not migrated automatically.\n\n"
    "SOURCE C (changelog): BREAKING: the --theme flag is renamed to --style. "
    "Startup time improved by 40%."
)

TASK = {
    "id": "T06",
    "title": "Synthesize release research",
    "category": "research-synthesis",
    "prompt": ("A user on X11 with a custom theme asks whether to upgrade omarchy-launcher. "
               "Using ONLY the sources below, write a summary of at most 120 words covering "
               "what is new and what would break for them.\n\n" + SOURCES),
    "checkers": [
        {"type": "contains_all", "values": ["fuzzy", "--style", "wayland"]},
        {"type": "length_max", "words": 140},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": True,
}