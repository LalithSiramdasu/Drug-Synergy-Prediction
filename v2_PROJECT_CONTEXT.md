Project: Drug Synergy Prediction / SynergyLens
Current stable branch: main, tag v1
Current working branch: chatbot-integration
Goal: Add chatbot integration without breaking existing v1 prediction, SHAP, molecules, batch, health, and model performance flows.
Active frontend: templates/index.html, static/css/app.css, static/js/app.js
Backend entry: app.py
Routes: backend/routes/api_routes.py
Core services: prediction_service.py, data_loader.py, model_loader.py, shap_service.py, batch_service.py, molecule_service.py
Prediction input: NSC1, NSC2, CELLNAME
Prediction flow: build 526 features, load Step 6 cell-line model, predict both drug orders, average ComboScore.