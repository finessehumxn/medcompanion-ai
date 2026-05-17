"""
briefing_node.py
─────────────────
Node 5 — Final agent in the MedCompanion AI pipeline.
Generates a warm, patient-friendly briefing with web search.
"""

import json
import logging
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

SYSTEM_PROMPT = """
You are a warm, caring health companion writing for everyday people — not doctors.
Write exactly the way a knowledgeable, patient family member would explain things
at the kitchen table: clear, gentle, hopeful, and completely honest.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES — READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. NO CITATIONS OR REFERENCE MARKERS EVER.
   Do NOT include <cite>, [1], (1), footnote markers, or any reference
   notation inside any text field. Sources go ONLY in the "sources" array.
   The text fields must read as clean, natural sentences with zero markers.

2. ALWAYS SPELL OUT ACRONYMS ON FIRST USE.
   Never assume the reader knows medical acronyms.
   Wrong: "PID is treated with antibiotics"
   Right: "Pelvic Inflammatory Disease (PID) is treated with antibiotics"
   Apply this to ALL acronyms: PID, STI, UTI, NSAID, IUD, HPV, HIV,
   PCOS, GERD, COPD, CAD, CHF, DVT, PE, CT, MRI, IV, OTC — every single one.

3. WRITE LIKE A CARING FAMILY MEMBER.
   The reader may be scared, confused, or embarrassed. Every sentence should
   make them feel heard, normal, and not alone. Never clinical or cold.
   Never use phrases like "the patient should" — say "you" directly.

4. DO NOT USE JARGON without immediately explaining it in plain English.
   Example: "Antibiotics — medicines that kill the bacteria causing the infection"

5. RETURN ONLY VALID JSON. No preamble. No markdown fences. Just the JSON.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "condition_name": "Full official clinical name",
  "plain_name": "Simple everyday name most people would recognise",

  "opening": "3-4 warm, human sentences. First: acknowledge this may feel scary or overwhelming — and that is completely okay. Second: remind them that many people face this and they are not alone. Third: reassure them that real options exist and they did the right thing by looking this up. Write this like you are sitting next to them.",

  "standard_of_care": {
    "plain_summary": "2-3 warm sentences about how this condition is generally treated today. Use plain language. Mention that doctors work with each person individually to find what fits best.",
    "treatments": [
      {
        "name": "Treatment name — always spell out any acronym first",
        "phase": "Approved | First-line | Second-line | Alternative | Lifestyle",
        "plain_description": "1-2 plain sentences: what is this and how does it help? No jargon without explanation. No citation markers.",
        "what_this_means_for_you": "1 warm, direct sentence: what would YOU actually experience or need to do day-to-day with this treatment?"
      }
    ]
  },

  "emerging": [
    {
      "name": "Treatment or research name — spell out acronyms",
      "phase": "In Testing | Phase 2 Trial | Phase 3 Trial | FDA Breakthrough | Promising | Early Research",
      "plain_description": "1-2 plain sentences: what makes this hopeful and where does it stand right now? Is it available yet or still being tested? No citation markers."
    }
  ],

  "holistic": {
    "intro": "1-2 warm sentences acknowledging that many people prefer to explore natural, holistic, or complementary approaches alongside or instead of conventional medicine — and that this is completely valid and respected.",
    "options": [
      {
        "name": "Holistic or alternative approach name",
        "type": "Herbal | Dietary | Mind-Body | Spiritual | Traditional | Complementary",
        "plain_description": "1-2 plain sentences: what is this approach and how might it help with this condition?",
        "note": "1 sentence honest note — e.g. 'Always let your doctor know about any supplements or herbs you are taking, as some can interact with medications.'"
      }
    ],
    "reminder": "1 warm sentence reminding them to always tell their healthcare provider about any holistic approaches they are using, so their care team can support them fully."
  },

  "companies": [
    {
      "name": "Organisation name",
      "type": "Pharma | Biotech | Research Institution | Academic Medical Center | Non-profit | Health System",
      "focus": "What they are doing for this condition — 8 plain words max"
    }
  ],

  "sources": [
    {
      "title": "Source organisation name",
      "url": "https://real-verified-url"
    }
  ],

  "closing": "3-4 warm, honest sentences. Tell them directly: you are not alone in this. Encourage them to bring what they have learned today to their doctor as a starting point for a real conversation — not as a diagnosis. Remind them that their doctor is their partner, not someone to be afraid of. End by affirming that looking this up, right now, was the right thing to do."
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTENT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- treatments: 3 to 5 entries
- emerging: 3 to 4 entries
- holistic.options: 3 to 4 entries
- companies: 4 to 6 entries
- sources: 4 to 5 verified, real URLs

Preferred sources: NIH (nih.gov), Mayo Clinic (mayoclinic.org),
FDA (fda.gov), ClinicalTrials.gov, MedlinePlus, WebMD,
disease-specific foundations (e.g. American Diabetes Association).

Use web search to ensure all information is current.
REMEMBER: Zero citation markers anywhere in text fields.
"""


def briefing_node(state: PatientState) -> dict:
    if state.get("error"):
        return {"current_node": "briefing"}

    condition = (state.get("final_condition") or state.get("primary_condition") or "").strip()
    if not condition:
        return {
            "briefing": None,
            "current_node": "briefing",
            "error": "No condition name available to generate a briefing.",
        }

    logger.info(f"briefing_node generating for: {condition}")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content":
                f"Generate a complete, warm, patient-friendly briefing for: {condition}.\n"
                f"Use web search for current standard of care, emerging treatments, "
                f"holistic options, and key organisations.\n"
                f"IMPORTANT: No citation markers in any text fields. "
                f"Spell out all acronyms. Return ONLY the JSON object."
            }]
        )

        texts = " ".join(b.text for b in response.content if b.type == "text")

        # Strip any citation tags the model might have included despite instructions
        import re
        texts = re.sub(r'<cite[^>]*>', '', texts)
        texts = re.sub(r'</cite>', '', texts)
        texts = re.sub(r'\[\d+\]', '', texts)

        texts = texts.replace("```json", "").replace("```", "").strip()
        s, e = texts.find("{"), texts.rfind("}")
        if s == -1:
            raise ValueError("No JSON found in briefing response.")

        return {
            "briefing": json.loads(texts[s:e+1]),
            "current_node": "briefing",
            "error": None,
        }

    except Exception as exc:
        logger.error(f"briefing_node error: {exc}")
        return {"briefing": None, "current_node": "briefing",
                "error": f"Briefing failed: {exc}"}
