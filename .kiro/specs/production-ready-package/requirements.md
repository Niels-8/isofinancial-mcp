# Requirements Document

## Introduction

Ce document définit les exigences pour transformer IsoFinancial-MCP en un package Python production-ready, prêt à être publié sur PyPI et utilisé dans des projets externes. Après l'implémentation de la spec data-reliability-improvement, le projet nécessite une refactorisation du code, une documentation claire sur la configuration des clés API, et une structure de package professionnelle. L'objectif est de créer un package installable, bien documenté, et facile à configurer pour les utilisateurs finaux.

## Glossary

- **Package**: Module Python installable via pip/uv avec structure standardisée
- **PyPI**: Python Package Index, dépôt public de packages Python
- **Configuration_System**: Système de gestion des paramètres utilisateur (clés API, cache, rate limits)
- **API_Key**: Clé d'authentification pour accéder aux services externes (Alpha Vantage, SerpAPI)
- **Documentation**: Ensemble de fichiers expliquant l'installation, la configuration et l'utilisation
- **Refactoring**: Restructuration du code pour améliorer la lisibilité et la maintenabilité
- **Production_Ready**: État d'un logiciel prêt pour utilisation en environnement réel
- **User_Guide**: Documentation destinée aux utilisateurs finaux
- **Developer_Guide**: Documentation destinée aux contributeurs et développeurs

## Requirements

### Requirement 1 - Code Refactoring

**User Story:** En tant que développeur, je veux une structure de code propre et cohérente dans datasources, afin de maintenir facilement le projet

#### Acceptance Criteria

1. THE Package SHALL éliminer les fichiers en double dans datasources (earnings_source vs earnings_sources, trends_source vs trends_sources)
2. THE Package SHALL consolider la logique dans un seul fichier par source avec un pattern cohérent
3. THE Package SHALL utiliser le pattern : {source}_source.py pour les sources simples, {source}_source_manager.py pour les managers
4. THE Package SHALL déplacer toute la documentation MD hors du dossier reliability vers un emplacement approprié (docs/ ou .kiro/)
5. THE Package SHALL maintenir uniquement le code Python et les fichiers de configuration (YAML) dans les dossiers de code source

### Requirement 2 - Welcome Message

**User Story:** En tant qu'utilisateur final, je veux un message de bienvenue professionnel lors du démarrage du serveur MCP, afin de comprendre que j'utilise IsoFinancial-MCP et non FastMCP

#### Acceptance Criteria

1. THE Server SHALL afficher un message de bienvenue personnalisé au démarrage mentionnant "IsoFinancial-MCP"
2. THE Server SHALL supprimer toutes les références à "FastMCP" dans les messages utilisateur
3. THE Server SHALL afficher la version du package dans le message de bienvenue
4. THE Server SHALL indiquer les sources de données disponibles (avec/sans clés API)
5. THE Server SHALL afficher un message concis avec les instructions de base (comment obtenir de l'aide)

### Requirement 3 - MCP Configuration Tools

**User Story:** En tant qu'utilisateur du serveur MCP, je veux configurer les clés API directement via des outils MCP, afin de ne pas avoir à éditer manuellement des fichiers de configuration

#### Acceptance Criteria

1. THE Server SHALL exposer un outil MCP `configure_api_key` permettant de définir une clé API (provider, key)
2. THE Server SHALL exposer un outil MCP `get_configuration` retournant la configuration actuelle (sans exposer les clés complètes)
3. THE Server SHALL exposer un outil MCP `list_data_sources` montrant toutes les sources disponibles et leur statut (enabled/disabled, requires_key)
4. THE Server SHALL persister les clés API configurées via MCP dans le fichier de configuration utilisateur
5. THE Server SHALL valider les clés API lors de la configuration et retourner un message d'erreur clair si invalide

### Requirement 4 - Multi-Method Configuration

**User Story:** En tant qu'utilisateur, je veux configurer le serveur MCP via plusieurs méthodes (MCP tools, variables d'environnement, fichier YAML), afin de choisir la méthode la plus adaptée à mon workflow

#### Acceptance Criteria

1. THE Configuration_System SHALL supporter la configuration via outils MCP (priorité 1)
2. THE Configuration_System SHALL supporter les variables d'environnement (priorité 2)
3. THE Configuration_System SHALL supporter un fichier YAML à ~/.iso_financial_mcp/config/datasources.yaml (priorité 3)
4. THE Configuration_System SHALL fusionner les configurations avec ordre de priorité : MCP tools > env vars > YAML > defaults
5. THE Documentation SHALL expliquer clairement les trois méthodes de configuration avec des exemples pour chacune

### Requirement 5 - Documentation Structure

**User Story:** En tant que développeur, je veux une documentation bien organisée séparée du code source, afin de maintenir une structure propre

#### Acceptance Criteria

1. THE Package SHALL déplacer tous les fichiers MD du dossier reliability vers docs/ ou .kiro/specs/
2. THE Package SHALL créer un fichier docs/ARCHITECTURE.md expliquant la structure globale
3. THE Package SHALL créer un fichier docs/RELIABILITY.md consolidant la documentation de fiabilité
4. THE Package SHALL maintenir uniquement README.md, CHANGELOG.md, LICENSE à la racine
5. THE Package SHALL mettre à jour tous les liens internes après le déplacement

### Requirement 7 - Configuration Documentation

**User Story:** En tant qu'utilisateur, je veux une documentation claire sur la configuration des clés API, afin d'activer facilement les sources optionnelles

#### Acceptance Criteria

1. THE Documentation SHALL créer un fichier docs/CONFIGURATION.md dédié à la configuration
2. THE Documentation SHALL lister toutes les clés API optionnelles (Alpha Vantage, SerpAPI) avec leurs avantages
3. THE Documentation SHALL expliquer les 3 méthodes de configuration (MCP tools, env vars, YAML) avec exemples
4. THE Documentation SHALL inclure des liens directs vers les sites d'inscription pour chaque API
5. THE Documentation SHALL inclure une section troubleshooting pour les erreurs courantes

### Requirement 8 - Tests Verification

**User Story:** En tant que développeur, je veux vérifier que les tests existants couvrent bien les nouvelles fonctionnalités, afin de maintenir la qualité du code

#### Acceptance Criteria

1. THE Package SHALL vérifier la couverture de tests actuelle et identifier les gaps
2. THE Package SHALL ajouter des tests pour les nouveaux outils MCP de configuration
3. THE Package SHALL ajouter des tests pour le refactoring des datasources
4. THE Package SHALL maintenir une couverture de tests d'au moins 80%
5. THE Package SHALL documenter comment exécuter les tests dans README.md

### Requirement 9 - MCP Health Check Tools

**User Story:** En tant qu'utilisateur du serveur MCP, je veux vérifier le statut des sources de données via un outil MCP, afin de diagnostiquer les problèmes sans quitter mon environnement MCP

#### Acceptance Criteria

1. THE Server SHALL exposer un outil MCP `get_health_status` retournant le statut de toutes les sources
2. THE Server SHALL inclure dans le health check : connectivité réseau, validité des clés API, statut du cache, success rate
3. THE Server SHALL retourner un format structuré avec : source_name, status (healthy/degraded/unhealthy), success_rate, last_success, error_message
4. THE Server SHALL permettre de tester une source spécifique avec `test_data_source(source_name, ticker)`
5. THE Documentation SHALL expliquer comment utiliser les outils de diagnostic MCP

### Requirement 10 - CHANGELOG Accuracy

**User Story:** En tant qu'utilisateur, je veux un CHANGELOG avec des dates précises basées sur l'historique Git, afin de comprendre la chronologie réelle du projet

#### Acceptance Criteria

1. THE CHANGELOG SHALL utiliser les dates réelles des commits Git pour chaque version
2. THE CHANGELOG SHALL vérifier l'historique Git avec `git log --all --date=short` pour obtenir les dates exactes
3. THE CHANGELOG SHALL corriger les dates hallucinées ou estimées avec les vraies dates
4. THE CHANGELOG SHALL maintenir l'ordre chronologique correct des versions
5. THE CHANGELOG SHALL inclure les dates au format YYYY-MM-DD pour chaque version
