import pandas as pd
import io
from datetime import datetime, timedelta

def validate_excel_file(df):
    """
    Valide le format du fichier Excel importé
    
    Args:
        df (pandas.DataFrame): DataFrame à valider
        
    Returns:
        tuple: (is_valid, message) - un booléen indiquant si le fichier est valide et un message
    """
    # Vérifier les noms de colonnes alternatifs
    column_mapping = {
        "Tâche": ["Tâche", "Tache", "Task", "Nom", "Name"],
        "Date de début": ["Date de début", "Date début", "Start Date", "Début", "Start"],
        "Date de fin": ["Date de fin", "Date fin", "End Date", "Fin", "End"]
    }
    
    # Vérifier que les colonnes requises existent
    missing_columns = []
    for req_col, alternatives in column_mapping.items():
        if not any(alt in df.columns for alt in alternatives):
            missing_columns.append(req_col)
    
    if missing_columns:
        return False, f"Colonnes manquantes : {', '.join(missing_columns)}"
    
    # Standardiser les noms de colonnes
    df_columns = df.columns.tolist()
    for std_col, alternatives in column_mapping.items():
        for col in df_columns:
            if col in alternatives and col != std_col:
                df.rename(columns={col: std_col}, inplace=True)
                break
    
    # Vérifier que les dates sont valides
    try:
        for date_col in ["Date de début", "Date de fin"]:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        if df["Date de début"].isna().any() or df["Date de fin"].isna().any():
            return False, "Certaines dates sont invalides"
        
        # Vérifier que la date de fin est après la date de début
        if (df["Date de fin"] < df["Date de début"]).any():
            return False, "Certaines dates de fin sont antérieures aux dates de début"
    except Exception as e:
        return False, f"Erreur lors du traitement des dates : {str(e)}"
    
    return True, "Le fichier est valide"

def generate_example_excel():
    """
    Génère un fichier Excel d'exemple
    
    Returns:
        bytes: Contenu du fichier Excel
    """
    # Dates relatives pour l'exemple (par rapport à aujourd'hui)
    today = datetime.now().date()
    start_date = today - timedelta(days=15)
    
    # Données d'exemple
    data = {
        "Tâche": [
            "Analyse des besoins",
            "Conception",
            "Développement backend",
            "Développement frontend",
            "Tests unitaires",
            "Tests d'intégration",
            "Déploiement"
        ],
        "Date de début": [
            start_date,
            start_date + timedelta(days=14),
            start_date + timedelta(days=30),
            start_date + timedelta(days=45),
            start_date + timedelta(days=60),
            start_date + timedelta(days=75),
            start_date + timedelta(days=90)
        ],
        "Date de fin": [
            start_date + timedelta(days=13),
            start_date + timedelta(days=29),
            start_date + timedelta(days=50),
            start_date + timedelta(days=65),
            start_date + timedelta(days=70),
            start_date + timedelta(days=85),
            start_date + timedelta(days=97)
        ],
        "Responsable": [
            "Alice Martin",
            "Thomas Dubois",
            "Sophie Bernard",
            "Nicolas Lambert",
            "Thomas Dubois",
            "Sophie Bernard",
            "Nicolas Lambert"
        ],
        "Statut": [
            "Terminé",
            "Terminé",
            "En cours",
            "En cours",
            "Non démarré",
            "Non démarré",
            "Non démarré"
        ],
        "Priorité": [
            "Haute",
            "Haute",
            "Critique",
            "Critique",
            "Moyenne",
            "Moyenne",
            "Haute"
        ],
        "Dépendances": [
            "",
            "Analyse des besoins",
            "Conception",
            "Conception",
            "Développement backend",
            "Développement frontend, Tests unitaires",
            "Tests d'intégration"
        ],
        "Description": [
            "Recueillir et analyser les besoins du client",
            "Conception de l'architecture et des interfaces",
            "Développement des fonctionnalités backend",
            "Développement des interfaces utilisateur",
            "Tests unitaires pour chaque module",
            "Tests d'intégration entre modules",
            "Mise en production de l'application"
        ]
    }
    
    # Créer le DataFrame
    df = pd.DataFrame(data)
    
    # Convertir en Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Projet Exemple', index=False)
        
        # Ajuster la largeur des colonnes
        worksheet = writer.sheets['Projet Exemple']
        for i, col in enumerate(df.columns):
            # Définir une largeur minimale pour chaque colonne
            column_width = max(len(col) + 2, df[col].astype(str).map(len).max() + 2)
            worksheet.set_column(i, i, column_width)
    
    output.seek(0)
    return output.getvalue()

def calculate_project_stats(df):
    """
    Calcule diverses statistiques sur un projet
    
    Args:
        df (pandas.DataFrame): DataFrame contenant les données du projet
        
    Returns:
        dict: Statistiques du projet
    """
    if df.empty:
        return {
            "total_tasks": 0,
            "completed_tasks": 0,
            "completion_rate": 0,
            "critical_tasks": 0,
            "duration": 0,
            "delayed_tasks": 0
        }
    
    total_tasks = len(df)
    completed_tasks = len(df[df["Statut"] == "Terminé"])
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    critical_tasks = len(df[df["Priorité"] == "Critique"])
    delayed_tasks = len(df[df["Statut"] == "En retard"])
    
    # Calculer la durée totale du projet en jours
    min_date = df["Date de début"].min()
    max_date = df["Date de fin"].max()
    duration = (max_date - min_date).days + 1
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": completion_rate,
        "critical_tasks": critical_tasks,
        "duration": duration,
        "delayed_tasks": delayed_tasks
    }