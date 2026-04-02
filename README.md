# GenFlix - Recommandation de séries

GenFlix est une application web de recommandation de séries TV. L'objectif est de concevoir une plateforme permettant à un utilisateur d'obtenir des recommandations personnalisées générées par une IA en fonction de ses goûts et de ses précédentes écoutes. Les informations utiles de l'utilisateur et des séries persistent dans une base de données locale.

Ce projet s'appuie sur deux API principales :
* **TVmaze API** : pour rechercher et enrichir les informations sur les séries (résumé, image, genres, etc.).
* **Google Gemini API** : pour analyser les goûts d'un utilisateur et générer des recommandations de manière intelligente.

---

## 🌟 Fonctionnalités principales

L'application permet aux utilisateurs de :
* **S'inscrire, se connecter et se déconnecter** en toute sécurité.
* **Sélection initiale (Onboarding)** : Sélection des séries déjà vues et aimées dès la première connexion (création du profil de base).
* **Recommandations IA (Gemini)** : Génération de séries recommandées basées sur l'historique de l'utilisateur (séries aimées, non aimées). Chaque recommandation inclut :
    * Un *pitch* accrocheur généré par l'IA.
    * Une *explication* détaillée du pourquoi cette série correspond aux goûts de l'utilisateur.
* **Texte de recommandation personnalisable** : L'utilisateur peut modifier le texte d'instruction de recommandation généré par Gemini pour affiner les futurs résultats.
* **Recherche de séries** : Recherche par nom via l'API TVmaze.
* **Avis et ressentis** : Possibilité d'indiquer son opinion sur n'importe quelle série (Aimé, Neutre, N'aime pas) afin d'ajuster progressivement ses préférences.
* **Statistiques** : Génération d'un graphique (Chart) représentant la répartition des genres de séries selon les avis de l'utilisateur.

---

## 🛠️ Prérequis

Avant de commencer, assurez-vous d'avoir installé sur votre machine :
* [Python 3.10+](https://www.python.org/downloads/)
* Une clé d'API Google Gemini (à récupérer sur [Google AI Studio](https://aistudio.google.com/api-keys))

---

## 🚀 Installation et mise en place

Suivez ces étapes pour exécuter le projet localement.

### 1. Cloner le projet
Si vous utilisez Git, clonez le dépôt et déplacez-vous dans le dossier du projet :
```bash
git clone <URL_DU_DEPOT>
cd GenFlix
```

### 2. Créer et activer un environnement virtuel (venv)
Il est fortement recommandé d'utiliser un environnement virtuel pour isoler les dépendances du projet.

**Sur Windows :**
```bash
python -m venv venv
venv\Scripts\activate
```

**Sur macOS et Linux :**
```bash
python3 -m venv venv
source venv/bin/activate
```
*(Une fois activé, vous devriez voir `(venv)` apparaître au début de votre ligne de commande).*

### 3. Installer les dépendances
Utilisez le fichier `requirements.txt` pour installer toutes les bibliothèques nécessaires (Flask, SQLAlchemy, etc.) :
```bash
pip install -r requirements.txt
```

### 4. Configuration des variables d'environnement
Le projet utilise des variables d'environnement pour stocker les informations sensibles (comme la clé API Gemini).
1. Copiez le fichier `.env.template` et renommez-le en `.env`.
2. Ouvrez le fichier `.env` et ajoutez votre clé API Gemini (et toute autre configuration requise par votre projet).

```env
# Contenu du .env
GEMINI_API_KEY=votre_cle_api_ici
```

### 5. Initialiser la base de données
L'application utilise SQLite (`instance/GenFlixBD.db`). Pour initialiser la base de données avec les modèles définis dans `backend/models.py`, assurez-vous que la commande de création est exécutée (souvent géré au premier lancement par Flask-SQLAlchemy ou via les commandes Flask appropriées selon votre `app.py`).

### 6. Lancer l'application
Démarrez le serveur de développement Flask :
```bash
python app.py
# ou
flask run
```

L'application sera accessible depuis votre navigateur à l'adresse suivante : **http://127.0.0.1:5000**

---

## 📁 Architecture du projet

* `app.py` : Point d'entrée de l'application Flask.
* `backend/` : Logique métier de l'application.
    * `models.py` : Définition des tables de la base de données (User, Serie, Opinion, Recommendation).
    * `routes/` : Définition des endpoints (`web.py` pour les vues HTML, `api.py` pour les appels AJAX/JSON).
    * `providers/` : Scripts de connexion aux API externes (TVmaze, Gemini).
    * `enums/` : Énumérations (Types d'opinions, statuts HTTP).
* `instance/` : Contient la base de données SQLite locale (`GenFlixBD.db`).
* `static/` : Fichiers statiques (CSS, images, JavaScript).
* `templates/` : Fichiers HTML (rendus avec Jinja2).
* `requirements.txt` : Liste des librairies Python requises.

---

## 🔮 Améliorations possibles (Perspectives)

Bien que l'application soit fonctionnelle, plusieurs pistes d'améliorations ont été identifiées mais n'ont pas pu être implémentées :

* **Feedback visuel lors de la génération IA** : Ajouter un indicateur de chargement (loader/spinner) explicite lors des appels à l'API Gemini. Cela permettrait à l'utilisateur de mieux comprendre qu'un traitement complexe est en cours d'exécution en arrière-plan.
* **Mise en place de tests automatisés** : Intégrer une suite de tests pour garantir la robustesse de l'application sur le long terme :
    * *Tests unitaires* : Pour vérifier la logique métier, la génération des requêtes IA et les utilitaires.
    * *Tests fonctionnels* : Pour s'assurer du bon comportement des routes API.
    * *Tests End-to-End (E2E)* : Pour simuler et valider le parcours utilisateur complet (de l'inscription à la recommandation).
* **Gestion avancée des retours d'erreurs API** : Améliorer la précision et la structure des messages d'erreur renvoyés par l'API (ex: codes spécifiques, stack trace en mode développement). Cela faciliterait grandement le débogage et la compréhension des problèmes rencontrés lors du développement.

---

## 💡 Fonctionnalités imaginées (Mises de côté par manque de temps)

Afin de respecter les délais du projet et de garantir une application stable, certaines idées ambitieuses ont été écartées lors de la phase de conception. Voici deux fonctionnalités majeures que nous aurions aimé développer :

### 1. Chatbot de recommandation contextuelle (Mood & Contexte)
* **Le concept** : Au lieu d'une simple page de recommandations, l'utilisateur pourrait interagir avec un chatbot. L'IA poserait quelques questions conversationnelles pour cerner son état d'esprit actuel, le contexte de visionnage (seul, en couple, en famille, entre amis), son âge, ou encore le temps dont il dispose. En fin d'échange, l'IA proposerait une liste de séries parfaitement adaptée à "l'instant T".
* **Mise en place technique** : 
    * **Front-end** : Création d'une interface de messagerie classique en HTML/CSS/JS (bulles de chat, zone de saisie) avec des questions déjà écrites.
    * **Back-end** : Ajout d'une route API dans Flask capable de stocker et de maintenir l'historique de la conversation dans la session utilisateur.
    * **IA** : Utilisation de l'API Gemini pour trouver des recommandations basées sur les réponses fournies par l'utilisateur. 

### 2. Découverte de séries façon "Tinder" (Swipe & Profils IA)
* **Le concept** : Une interface ludique reprenant le principe du *swipe* (glisser à droite pour "Aimé", à gauche pour "N'aime pas"). Pour rendre l'expérience plus amusante et originale, l'IA générerait pour chaque série une "bio" façon profil de site de rencontre, en remplacement du résumé textuel classique.
* **Mise en place technique** :
    * **Front-end** : Utilisation d'une librairie JavaScript spécialisée dans les gestes tactiles (comme *Hammer.js* ou *TinderCards*) pour gérer la physique des cartes et les événements de balayage.
    * **Back-end & IA** : Lors de la récupération d'une série via TVmaze, le backend ferait un appel à Gemini pour réécrire le résumé sous la forme d'un profil de rencontre (ex: *"Je suis une série dramatique, un peu sombre, cherchant quelqu'un pour des soirées intenses sous un plaid..."*). Ces descriptions générées seraient mises en cache dans notre base de données SQLite (table `Serie`) pour limiter les coûts et les temps d'appel à l'API.
    * **Base de données** : Chaque action de balayage déclencherait un appel asynchrone vers notre endpoint existant `/api/set_opinion` pour enregistrer immédiatement le choix de l'utilisateur.