
NCI ALMANAC Drug Combination ComboScore Prediction Project
==========================================================

PROJECT STATUS
--------------
Step 1  : FG-only ComboScore created
Step 2  : Drug features cleaned
Step 2B : Missing drug investigation completed
Step 2C : Missing drug features recovered
Step 3  : Model matrix created
Step 4  : One-cell-line model test completed
Step 5  : Official evaluation completed
Step 6  : Final 60 models trained on 100% data
Step 7A : Official test-set prediction checking completed
Step 7B : Single custom prediction completed
Step 7C : Batch custom prediction completed
Step 8  : Final summary files created


IMPORTANT FINAL DECISION
------------------------
Official evaluation metrics come from Step 5.

Step 6 final models are trained on 100% data for prediction/deployment.
Therefore Step 6 is not used for test metrics.

The failed optimized Step 6 experiment with interaction features was rejected because
it performed worse than the Step 5 baseline.


OFFICIAL BEST OVERALL MODEL
---------------------------
Best average model by Step 5 mean R2:
Model       : CatBoost
Mean R2     : 0.3748176022281819
Mean Rp     : 0.6179048740464373


FINAL MODEL COUNTS
------------------
       model  final_model_count  percentage
    CatBoost                 17       28.33
    LightGBM                 17       28.33
RandomForest                 15       25.00
     XGBoost                 11       18.33


DATA SUMMARY
------------
Available drugs       : 100
Available cell lines  : 60
Final model features  : 526
Final saved models    : 60


FINAL PREDICTION FLOW
---------------------
Input:
    NSC1
    NSC2
    CELLNAME

Process:
    1. Load data/drug_features.csv
    2. Get 263 features for NSC1
    3. Get 263 features for NSC2
    4. Create 526 model features:
           D1_feat_0 ... D1_feat_262
           D2_feat_0 ... D2_feat_262
    5. Load correct model for CELLNAME using step6_final_model_registry.csv
    6. Predict NSC1 -> NSC2
    7. Predict NSC2 -> NSC1
    8. Average both predictions
    9. Return final predicted ComboScore


FILES NEEDED FOR FLASK APP
--------------------------
1. data/drug_features.csv
2. data/step6_final_model_feature_columns.json
3. results/step6_final_model_registry.csv
4. models/final_step6_*.pkl


IMPORTANT FOLDERS
-----------------
Project folder:
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3

Data folder:
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3\data

Results folder:
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3\results

Models folder:
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3\models

Predictions folder:
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3\predictions

Final summary folder:
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3\final_project_summary


FINAL SUMMARY FILES CREATED
---------------------------
1. final_model_performance_summary.csv
2. final_best_models_per_cellline.csv
3. final_model_counts.csv
4. final_available_inputs.csv
5. final_flask_assets_manifest.csv
6. final_pipeline_files_summary.csv
7. final_project_readme.txt
8. available_cell_lines.txt
9. available_drug_nscs.txt


NOTE FOR CODEX / FLASK FRONTEND
-------------------------------
Use the Step 7B logic for single prediction in Flask.

The Flask app should:
    - Accept NSC1, NSC2, CELLNAME from user
    - Validate NSCs using drug_features.csv
    - Validate cell line using step6_final_model_registry.csv
    - Build the 526-feature input row
    - Load the correct final model
    - Predict both drug orders
    - Return the average predicted ComboScore

