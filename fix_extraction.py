import os
FILE = os.path.join('frontend', 'index.html')
with open(FILE, 'r', encoding='utf-8') as f:
    h = f.read()

# Fix 1: count all extracted fields
old = 'var total = (ex.symptoms ? ex.symptoms.length : 0) + (ex.body_parts ? ex.body_parts.length : 0);'
new = 'var total = (ex.symptoms ? ex.symptoms.length : 0) + (ex.body_parts ? ex.body_parts.length : 0) + (ex.emotional_context ? ex.emotional_context.length : 0) + (ex.conditions_mentioned ? ex.conditions_mentioned.length : 0) + (ex.medications ? ex.medications.length : 0);'
h = h.replace(old, new)

# Fix 2: better message when total is 0
old2 = "'<p class=\"heard-intro\">I picked up on <strong>' + total + ' things</strong> you shared with me:</p>'"
new2 = "'<p class=\"heard-intro\">' + (total > 0 ? 'I picked up on <strong>' + total + ' things</strong> you shared with me:' : 'Here is what I understand from what you shared:') + '</p>'"
h = h.replace(old2, new2)

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(h)
print('Done')
