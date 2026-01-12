#!/usr/bin/env python3
"""Script Python pour corriger la route /me dans nginx"""

import re
import subprocess
import sys
from datetime import datetime

CONFIG_FILE = "/etc/nginx/sites-available/default"
BACKUP_FILE = f"{CONFIG_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def main():
    print("Sauvegarde de la configuration...")
    try:
        # Lire le fichier
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        # Sauvegarder
        with open(BACKUP_FILE, 'w') as f:
            f.write(content)
        print(f"✓ Sauvegarde créée: {BACKUP_FILE}")
        
        # Remplacer le bloc location /me
        # Pattern pour trouver le bloc location ~ ^/me$ ou location /me
        pattern = r'    location\s+~\s+\^/me\$ \{.*?\n    \}'
        
        replacement = '''    location /me {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }'''
        
        # Essayer avec le pattern regex d'abord
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Si pas de changement, essayer avec location /me simple
        if new_content == content:
            pattern2 = r'    location\s+/me\s+\{.*?\n    \}'
            new_content = re.sub(pattern2, replacement, content, flags=re.DOTALL)
        
        # Si toujours pas de changement, chercher et remplacer manuellement
        if new_content == content:
            lines = content.split('\n')
            new_lines = []
            skip_until_brace = False
            for i, line in enumerate(lines):
                if 'location' in line and 'me' in line:
                    skip_until_brace = True
                    new_lines.append('    location /me {')
                    new_lines.append('        proxy_pass http://127.0.0.1:8000;')
                    new_lines.append('        proxy_set_header Host $host;')
                    new_lines.append('        proxy_set_header X-Real-IP $remote_addr;')
                    new_lines.append('        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;')
                    new_lines.append('        proxy_set_header X-Forwarded-Proto $scheme;')
                    new_lines.append('    }')
                    continue
                if skip_until_brace:
                    if line.strip() == '}':
                        skip_until_brace = False
                    continue
                new_lines.append(line)
            new_content = '\n'.join(new_lines)
        
        # Écrire le nouveau contenu
        with open(CONFIG_FILE, 'w') as f:
            f.write(new_content)
        
        print("✓ Configuration modifiée")
        
        # Vérifier la syntaxe
        print("Vérification de la syntaxe nginx...")
        result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        
        if 'successful' in result.stdout:
            print("✓ Syntaxe OK")
            print("Rechargement de nginx...")
            reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
            if reload_result.returncode == 0:
                print("✓ Nginx rechargé avec succès!")
                return 0
            else:
                print("✗ Erreur lors du rechargement:")
                print(reload_result.stderr)
                return 1
        else:
            print("✗ Erreur de syntaxe:")
            print(result.stderr)
            print("Restauration de la sauvegarde...")
            with open(BACKUP_FILE, 'r') as f:
                backup_content = f.read()
            with open(CONFIG_FILE, 'w') as f:
                f.write(backup_content)
            return 1
            
    except PermissionError:
        print("✗ Erreur de permissions. Exécutez avec sudo:")
        print(f"  sudo python3 {sys.argv[0]}")
        return 1
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
