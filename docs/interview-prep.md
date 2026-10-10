# Préparation entretien PM technique Datadog

## Le récit en 90 secondes

« J'ai construit une petite API pour mettre à l'épreuve mon analyse du parcours
Datadog. Le résumé fournit une référence simple ; les flashcards distinguent
succès du fournisseur et validité de la réponse ; le quiz ajoute une chaîne de
deux appels. J'ai séparé instrumentation, diagnostic et qualité. Je peux montrer
les éléments vérifiés et nommer ce qui reste une hypothèse. »

Complète avec **une observation réellement documentée**, son impact utilisateur
et une proposition de test produit. N'annonce pas une corrélation APM démontrée
avant d'avoir suivi une trace entre les deux vues.

## Ce qu'il faut savoir expliquer au tableau

| Sujet | Explication attendue |
| --- | --- |
| Trace et span | La trace relie une requête et ses étapes ; chaque span décrit une opération et sa durée. Le quiz fait deux appels séquentiels. |
| APM et observabilité LLM | APM éclaire la requête applicative ; les spans LLM ajoutent messages, modèle, tokens et erreurs du fournisseur. La qualité demande une évaluation supplémentaire. |
| SDK et fournisseur | Le code utilise le SDK OpenAI, mais envoie les requêtes à Google. Le nom de l'intégration ne suffit pas à identifier le fournisseur facturé. |
| Auto-instrumentation | Les appels SDK sont capturés automatiquement ; le regroupement métier et la validation utilisent ici un workflow explicite. |
| Agentless | Pratique pour voir les appels LLM ; la configuration de référence désactive explicitement APM. Le SDK installé a aussi un chemin d'export APM sans Agent : vérifier le mode exact et les liens réels. |
| Erreurs | 422 = entrée rejetée ; 502 = fournisseur en échec ou sortie invalide ; 200 peut quand même contenir une réponse factuellement mauvaise. |
| Tokens et coût | Distinguer entrée et sortie ; vérifier fournisseur, modèle et tarification avant de traiter l'estimation comme une facture. |
| Latence | Séparer durée HTTP, appels LLM, attente et traitement. Un p95 sur deux appels n'est pas une référence robuste. |
| Auto-évaluation | Deux appels au même modèle peuvent partager la même erreur ; le verdict n'est ni une vérité terrain ni automatiquement une évaluation Datadog. |

## Démonstration de 7 minutes

1. **1 minute : problème utilisateur.** Un développeur/SRE constate une requête
   lente ou un contenu inutilisable et doit identifier l'étape responsable.
2. **1 minute : architecture.** FastAPI → SDK OpenAI → Gemini ; Datadog capture
   les appels ; expliquer le mode d'export réellement utilisé.
3. **2 minutes : une trace.** Décomposer le quiz et comparer ses deux appels.
   Montrer la corrélation APM seulement si elle a été vérifiée.
4. **2 minutes : un diagnostic.** Partir du symptôme, expliquer l'hypothèse,
   trouver l'étape fautive et montrer l'indice qui change la décision.
5. **1 minute : implication PM.** Nommer une friction, son utilisateur, une
   amélioration testable et la mesure qui permettrait de décider.

Prépare des captures de secours : une démonstration live dépend du quota, de la
latence du fournisseur et de l'ingestion. Garde les preuves sans données privées.

## Transformer une observation en raisonnement produit

Exemple à valider : le logo/fournisseur OpenAI apparaît pour un appel Gemini.

- **Utilisateur :** développeur qui adopte une API compatible OpenAI pour changer
  de modèle sans réécrire son application.
- **Problème :** attribution ambiguë ; confiance réduite dans le diagnostic et
  dans les coûts affichés.
- **Hypothèses concurrentes :** détection basée sur l'URL, modèle non reconnu,
  configuration incomplète, comportement propre à une version du SDK.
- **Proposition :** afficher séparément intégration SDK et fournisseur détecté,
  puis tester une indication claire lorsque l'attribution reste incertaine.
- **Mesure :** temps pour identifier correctement le fournisseur et proportion
  de configurations compatibles mal attribuées ; suivre aussi les faux positifs.
- **Priorisation :** estimer fréquence, impact et nombre d'utilisateurs concernés
  avant de généraliser à partir de cette expérience individuelle.

Autre angle : réduire le temps entre « j'ai installé le SDK » et « j'ai retrouvé
une première requête et son contexte APM ». Mesurer temps de réussite, taux
d'abandon et nombre d'étapes de dépannage ; ne pas inventer de valeurs.

## Questions à répéter à voix haute

- Pourquoi trois endpoints plutôt qu'une application complète ?
- Comment sais-tu qu'un HTTP 200 ne signifie pas que le produit fonctionne ?
- Quelle partie de ton hypothèse centrale as-tu réellement démontrée ?
- Que ferais-tu si les tokens apparaissaient, mais pas le coût ni le lien APM ?
- Pourquoi ton moniteur porte-t-il sur les workflows plutôt que tous les spans ?
- Pourquoi ne pas réessayer automatiquement chaque requête en erreur ?
- Comment évaluerais-tu la qualité avec dix exemples relus par une personne ?
- Que changerais-tu pour passer de ce prototype à un service public ?
- Quelle amélioration produit testerais-tu d'abord, et quelle preuve te ferait
  abandonner cette idée ?

Réponds avec : observation → explication technique → impact utilisateur →
arbitrage → mesure. Les tests automatisés sont une preuve du contrat logiciel,
pas une preuve de fiabilité du modèle ou de satisfaction des utilisateurs.

## Formulation portfolio

« Study Buddy — projet en cours : API FastAPI utilisant Gemini, instrumentée
pour étudier les traces LLM, les erreurs de sortie et les workflows multi-appels.
Validation APM et expérimentation des alertes : statut détaillé dans le journal
d'expériences. »

Actualise cette formulation avec les résultats réels de `audit.md`. Préfère une
limite clairement reconnue à une affirmation trop large comme « observabilité
de bout en bout entièrement validée ».
