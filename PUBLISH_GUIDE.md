# Guide de Publication sur PyPI

## 🚀 Étapes pour publier IsoFinancial-MCP sur PyPI

### 1. Préparation

Le projet est maintenant prêt pour la publication. Voici ce qui a été configuré :

- ✅ Structure du package correcte
- ✅ `pyproject.toml` configuré avec tes informations (Niels-8)
- ✅ Build testé et fonctionnel
- ✅ Package testé localement

### 2. Vérification avant publication

```bash
# Vérifier que le build fonctionne
uv run python -m build

# Tester le package localement
uv run python -c "import iso_financial_mcp; print('✅ Package works')"
```

### 3. Publication sur PyPI

#### Option A: Avec twine (recommandé)

```bash
# Installer twine
uv add twine

# Vérifier le package avant upload
uv run twine check dist/*

# Uploader sur PyPI
uv run twine upload dist/*
```

#### Option B: Avec uv

```bash
# Publier directement avec uv
uv run python -m twine upload dist/*
```

### 4. Informations de connexion

Quand tu seras invité à te connecter :
- **Username**: `Niels-8`
- **Password**: Ton mot de passe PyPI ou token API

### 5. Vérification après publication

Après la publication, vérifie que ton package est en ligne :
- https://pypi.org/project/iso-financial-mcp/

### 6. Installation et test

Une fois publié, teste l'installation :

```bash
# Installer depuis PyPI
pip install iso-financial-mcp

# Tester l'import
python -c "import iso_financial_mcp; print('✅ Successfully installed from PyPI')"
```

### 7. Utilisation après publication

Les utilisateurs pourront installer ton package avec :

```bash
pip install iso-financial-mcp
```

Et l'utiliser comme ceci :

```python
from iso_financial_mcp import server

# Démarrer le serveur
server.run()
```

## 📋 Checklist avant publication

- [x] Structure du package correcte
- [x] `pyproject.toml` configuré
- [x] Build testé
- [x] Package testé localement
- [x] README.md à jour
- [x] LICENSE MIT
- [ ] Compte PyPI configuré
- [ ] Token API ou mot de passe prêt

## 🎯 Prochaines étapes

1. **Créer un compte PyPI** si tu n'en as pas déjà un
2. **Configurer l'authentification** (token API recommandé)
3. **Publier le package** avec les commandes ci-dessus
4. **Tester l'installation** depuis PyPI
5. **Mettre à jour la documentation** GitHub

## 🔧 Dépannage

### Erreur de nom déjà pris
Si le nom `iso-financial-mcp` est déjà pris, change le nom dans `pyproject.toml` :
```toml
name = "iso-financial-mcp-niels8"  # ou un autre nom unique
```

### Erreur d'authentification
Utilise un token API PyPI au lieu du mot de passe :
1. Va sur https://pypi.org/manage/account/token/
2. Crée un nouveau token
3. Utilise ce token comme mot de passe

### Erreur de build
Vérifie que tous les fichiers sont présents :
```bash
ls -la iso_financial_mcp/
```

---

**Ton package est prêt pour la publication ! 🚀** 