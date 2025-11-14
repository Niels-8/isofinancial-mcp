# Requirements Document

## Introduction

Ce document définit les exigences pour améliorer la fiabilité et la disponibilité des sources de données financières dans le système IsoFinancial-MCP. Le système récupère actuellement des données depuis plusieurs sources externes (SEC, Google Trends, Nasdaq) qui présentent des problèmes de fiabilité : données manquantes, erreurs de rate limiting (429), et sources non fonctionnelles. L'objectif est d'implémenter des mécanismes de fallback, retry, et sources alternatives pour garantir une disponibilité maximale des données.

## Glossary

- **DataSource**: Module responsable de la récupération de données depuis une API externe spécifique
- **SEC_Source**: DataSource pour les filings SEC via l'API EDGAR
- **Trends_Source**: DataSource pour les données Google Trends via pytrends
- **Earnings_Source**: DataSource pour les calendriers d'earnings via Yahoo Finance et Nasdaq
- **Rate_Limiting**: Limitation du nombre de requêtes imposée par une API externe (erreur 429)
- **Fallback_Mechanism**: Système permettant de basculer vers une source alternative en cas d'échec
- **Retry_Strategy**: Stratégie de nouvelle tentative avec backoff exponentiel
- **Cache_Layer**: Système de mise en cache pour réduire les appels API
- **Alternative_Source**: Source de données secondaire utilisée quand la source primaire échoue

## Requirements

### Requirement 1

**User Story:** En tant qu'utilisateur du système MCP, je veux que les données SEC soient toujours disponibles, afin de pouvoir analyser les filings réglementaires même si une source échoue

#### Acceptance Criteria

1. WHEN THE SEC_Source échoue à récupérer des données, THE DataSource SHALL tenter une source alternative
2. WHERE une Alternative_Source est configurée, THE SEC_Source SHALL utiliser au moins deux sources différentes (EDGAR API et SEC RSS feeds)
3. IF THE SEC_Source ne retourne aucun filing après 30 jours de lookback, THEN THE DataSource SHALL étendre automatiquement la période de recherche à 90 jours
4. THE SEC_Source SHALL mettre en cache les résultats avec un TTL de 6 heures pour réduire les appels API
5. WHEN toutes les sources échouent, THE SEC_Source SHALL retourner les données en cache même si elles sont expirées, avec un indicateur "stale_data"

### Requirement 2

**User Story:** En tant qu'utilisateur du système MCP, je veux que les erreurs 429 de Google Trends soient gérées automatiquement, afin d'obtenir les données de tendances sans intervention manuelle

#### Acceptance Criteria

1. WHEN THE Trends_Source reçoit une erreur 429, THE DataSource SHALL implémenter un backoff exponentiel avec un délai initial de 10 secondes
2. THE Trends_Source SHALL limiter les requêtes à 1 requête toutes les 5 secondes (au lieu de 3 secondes actuellement)
3. IF THE Trends_Source échoue après 3 tentatives avec backoff, THEN THE DataSource SHALL utiliser une Alternative_Source (pytrends avec proxy ou SerpAPI)
4. THE Trends_Source SHALL ajouter un jitter aléatoire entre 1 et 3 secondes à chaque requête pour éviter la détection de patterns
5. WHEN THE Trends_Source détecte un taux d'erreur 429 supérieur à 50% sur les 10 dernières requêtes, THE DataSource SHALL activer automatiquement un mode "slow" avec 10 secondes entre requêtes

### Requirement 3

**User Story:** En tant qu'utilisateur du système MCP, je veux que les données d'earnings calendar soient toujours disponibles, afin de suivre les dates de publication des résultats financiers

#### Acceptance Criteria

1. WHEN THE Earnings_Source ne trouve pas de données sur Yahoo Finance, THE DataSource SHALL tenter automatiquement Nasdaq API
2. IF Nasdaq API échoue également, THEN THE Earnings_Source SHALL tenter une troisième source (Alpha Vantage ou Financial Modeling Prep)
3. THE Earnings_Source SHALL fusionner les données de plusieurs sources pour maximiser la couverture
4. WHEN aucune source ne retourne de données, THE Earnings_Source SHALL utiliser une estimation basée sur les patterns historiques (earnings typiquement 45 jours après fin de quarter)
5. THE Earnings_Source SHALL valider que les données retournées contiennent au moins une date future avant de les considérer valides

### Requirement 4

**User Story:** En tant qu'utilisateur du système MCP, je veux un système de monitoring des sources de données, afin d'identifier rapidement les sources défaillantes

#### Acceptance Criteria

1. THE DataSource SHALL enregistrer les métriques de succès/échec pour chaque source dans un fichier de log structuré
2. WHEN une source a un taux d'échec supérieur à 30% sur les 100 dernières requêtes, THE DataSource SHALL logger un warning avec les détails
3. THE DataSource SHALL exposer une fonction get_health_status() retournant le statut de santé de chaque source
4. THE DataSource SHALL inclure dans les logs : timestamp, ticker, source, succès/échec, temps de réponse, type d'erreur
5. WHEN une source est marquée comme "unhealthy", THE DataSource SHALL prioriser automatiquement les sources alternatives

### Requirement 5

**User Story:** En tant qu'utilisateur du système MCP, je veux que le système utilise intelligemment le cache, afin de minimiser les appels API et éviter les rate limits

#### Acceptance Criteria

1. THE Cache_Layer SHALL implémenter un système de cache à deux niveaux : mémoire (TTL court) et disque (TTL long)
2. WHEN une requête échoue avec une erreur 429, THE DataSource SHALL retourner les données en cache même si le TTL est expiré
3. THE Cache_Layer SHALL stocker les données sur disque avec un TTL de 7 jours pour les données peu volatiles (SEC filings, earnings history)
4. THE DataSource SHALL précharger le cache pour les tickers populaires (top 100 S&P 500) pendant les heures creuses
5. WHEN le cache contient des données de moins de 1 heure, THE DataSource SHALL retourner immédiatement le cache sans appeler l'API

### Requirement 6

**User Story:** En tant qu'utilisateur du système MCP, je veux des messages d'erreur clairs et actionnables, afin de comprendre pourquoi les données sont manquantes

#### Acceptance Criteria

1. WHEN une source échoue, THE DataSource SHALL retourner un objet d'erreur structuré avec : error_type, error_message, attempted_sources, fallback_used
2. THE DataSource SHALL distinguer les erreurs temporaires (429, timeout) des erreurs permanentes (ticker invalide, API deprecated)
3. WHEN des données partielles sont disponibles, THE DataSource SHALL les retourner avec un flag "partial_data" et la liste des sources manquantes
4. THE DataSource SHALL inclure dans la réponse le timestamp de la dernière mise à jour réussie pour chaque type de données
5. WHEN toutes les sources échouent, THE DataSource SHALL suggérer des actions correctives dans le message d'erreur (ex: "Retry in 60 seconds" ou "Check API key configuration")
