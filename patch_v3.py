import shutil, os, sys

FILE = os.path.join('frontend', 'index.html')
shutil.copy(FILE, FILE + '.bak')
print('Backup created')

with open(FILE, 'r', encoding='utf-8') as f:
    h = f.read()

# Fix 1: viewer_type
o1 = '        user_id: currentUser ? currentUser.user_id : null\n      })'
n1 = '        user_id: currentUser ? currentUser.user_id : null,\n        viewer_type: window.currentUserType || \'everyday\'\n      })'
h = h.replace(o1, n1)
print('Fix 1 done:', 'OK' if 'viewer_type' in h else 'SKIPPED')

# Fix 2: window.currentUserType
o2 = 'function setUserType(type) {\n  userType = type;'
n2 = 'function setUserType(type) {\n  window.currentUserType = type;\n  userType = type;'
h = h.replace(o2, n2)
print('Fix 2 done')

# Fix 3: footer email
h = h.replace('finessehumxn@gmail.com', 'hello@medcompanionai.com')
print('Fix 3 done')

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(h)
print('Saved. Now open VS Code to do Fix 4 (renderBriefing).')
