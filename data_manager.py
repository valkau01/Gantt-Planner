import os
import json
import pandas as pd
from datetime import datetime
import uuid

class DataManager:
    def __init__(self, data_dir="data/projects"):
        """
        Initialise le gestionnaire de données avec le répertoire de stockage
        
        Args:
            data_dir (str): Chemin vers le répertoire de stockage des projets
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_all_projects(self):
        """
        Charge tous les projets disponibles
        
        Returns:
            list: Liste des projets
        """
        projects = []
        
        if not os.path.exists(self.data_dir):
            return projects
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                project_path = os.path.join(self.data_dir, filename)
                
                try:
                    with open(project_path, 'r', encoding='utf-8') as f:
                        project = json.load(f)
                        projects.append(project)
                except Exception as e:
                    print(f"Erreur lors du chargement du projet {filename}: {str(e)}")
        
        # Trier par date de mise à jour (plus récent en premier)
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return projects
    
    def load_project(self, project_id):
        """
        Charge un projet spécifique par son ID
        
        Args:
            project_id (str): ID du projet à charger
            
        Returns:
            dict: Le projet chargé ou None si non trouvé
        """
        filename = f"{project_id}.json"
        project_path = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(project_path):
            return None
        
        try:
            with open(project_path, 'r', encoding='utf-8') as f:
                project = json.load(f)
                return project
        except Exception as e:
            print(f"Erreur lors du chargement du projet {project_id}: {str(e)}")
            return None
    
    def save_project(self, project):
        """
        Sauvegarde un projet
        
        Args:
            project (dict): Projet à sauvegarder
            
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        if not project or "id" not in project:
            return False
        
        filename = f"{project['id']}.json"
        project_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(project, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du projet {project['id']}: {str(e)}")
            return False
    
    def delete_project(self, project_id):
        """
        Supprime un projet
        
        Args:
            project_id (str): ID du projet à supprimer
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        filename = f"{project_id}.json"
        project_path = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(project_path):
            return False
        
        try:
            os.remove(project_path)
            return True
        except Exception as e:
            print(f"Erreur lors de la suppression du projet {project_id}: {str(e)}")
            return False
    
    def project_to_dataframe(self, project):
        """
        Convertit un projet en DataFrame pour affichage et manipulation
        
        Args:
            project (dict): Projet à convertir
            
        Returns:
            pandas.DataFrame: Données du projet
        """
        if not project or "tasks" not in project or not project["tasks"]:
            return pd.DataFrame()
        
        tasks_data = []
        for task in project["tasks"]:
            # Convertir les IDs de dépendances en noms de tâches
            dependency_names = []
            for dep_id in task.get("dependencies", []):
                for t in project["tasks"]:
                    if t["id"] == dep_id:
                        dependency_names.append(t["name"])
                        break
            
            tasks_data.append({
                "ID": task["id"],
                "Tâche": task["name"],
                "Date de début": pd.to_datetime(task["start_date"]),
                "Date de fin": pd.to_datetime(task["end_date"]),
                "Responsable": task["resource"],
                "Statut": task["status"],
                "Priorité": task["priority"],
                "Dépendances": ", ".join(dependency_names),
                "Description": task.get("description", "")
            })
        
        df = pd.DataFrame(tasks_data)
        
        # Calculer la durée de chaque tâche en jours
        if not df.empty:
            df["Durée"] = (df["Date de fin"] - df["Date de début"]).dt.days + 1
        
        return df
    
    def update_tasks_from_dataframe(self, project, df):
        """
        Met à jour les tâches d'un projet à partir d'un DataFrame modifié
        
        Args:
            project (dict): Projet à mettre à jour
            df (pandas.DataFrame): DataFrame contenant les données modifiées
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        if not project or "tasks" not in project:
            return False
        
        # Créer un mapping des noms de tâches aux IDs
        task_name_to_id = {task["name"]: task["id"] for task in project["tasks"]}
        
        for _, row in df.iterrows():
            task_id = row["ID"]
            
            # Trouver la tâche correspondante dans le projet
            for task in project["tasks"]:
                if task["id"] == task_id:
                    # Mettre à jour les champs
                    task["name"] = row["Tâche"]
                    task["start_date"] = row["Date de début"].date().isoformat()
                    task["end_date"] = row["Date de fin"].date().isoformat()
                    task["resource"] = row["Responsable"]
                    task["status"] = row["Statut"]
                    task["priority"] = row["Priorité"]
                    task["description"] = row["Description"]
                    
                    # Mettre à jour les dépendances
                    dependencies = []
                    if row["Dépendances"]:
                        dep_names = [name.strip() for name in row["Dépendances"].split(",")]
                        for dep_name in dep_names:
                            if dep_name in task_name_to_id:
                                dependencies.append(task_name_to_id[dep_name])
                    
                    task["dependencies"] = dependencies
                    break
        
        project["updated_at"] = datetime.now().isoformat()
        return self.save_project(project)
    
    def create_project_from_dataframe(self, df, project_name):
        """
        Crée un nouveau projet à partir d'un DataFrame importé
        
        Args:
            df (pandas.DataFrame): DataFrame contenant les données du projet
            project_name (str): Nom du projet
            
        Returns:
            dict: Le projet créé
        """
        # Vérifier et standardiser les noms de colonnes
        required_columns = ["Tâche", "Date de début", "Date de fin", "Responsable", "Statut", "Priorité"]
        
        # Renommer les colonnes si nécessaire
        column_mapping = {
            "Tâche": ["Tâche", "Tache", "Task", "Nom", "Name"],
            "Date de début": ["Date de début", "Date début", "Start Date", "Début", "Start"],
            "Date de fin": ["Date de fin", "Date fin", "End Date", "Fin", "End"],
            "Responsable": ["Responsable", "Resource", "Ressource", "Assigned To", "Assigné à"],
            "Statut": ["Statut", "Status", "État", "State"],
            "Priorité": ["Priorité", "Priority", "Importance"],
            "Dépendances": ["Dépendances", "Dependencies", "Dependances", "Prédécesseurs"],
            "Description": ["Description", "Notes", "Commentaire", "Details"]
        }
        
        # Standardiser les colonnes
        df_columns = df.columns.tolist()
        standardized_df = df.copy()
        
        for std_col, possible_names in column_mapping.items():
            for col in df_columns:
                if col in possible_names:
                    standardized_df = standardized_df.rename(columns={col: std_col})
                    break
        
        # Vérifier que toutes les colonnes requises existent
        for col in required_columns:
            if col not in standardized_df.columns:
                raise ValueError(f"Colonne requise manquante : {col}")
        
        # Convertir les dates si nécessaire
        for date_col in ["Date de début", "Date de fin"]:
            if standardized_df[date_col].dtype != 'datetime64[ns]':
                standardized_df[date_col] = pd.to_datetime(standardized_df[date_col], errors='coerce')
        
        # Ajouter les colonnes optionnelles si elles n'existent pas
        if "Dépendances" not in standardized_df.columns:
            standardized_df["Dépendances"] = ""
        
        if "Description" not in standardized_df.columns:
            standardized_df["Description"] = ""
        
        # Créer le nouveau projet
        project_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        project = {
            "id": project_id,
            "name": project_name,
            "created_at": now,
            "updated_at": now,
            "tasks": []
        }
        
        # Créer un mapping des noms de tâches (pour les dépendances)
        task_ids = {}
        for i, row in standardized_df.iterrows():
            task_id = f"task-{str(uuid.uuid4())[:8]}"
            task_ids[row["Tâche"]] = task_id
        
        # Créer les tâches
        for i, row in standardized_df.iterrows():
            # Gérer les dépendances
            dependencies = []
            if row["Dépendances"]:
                dep_names = [name.strip() for name in str(row["Dépendances"]).split(",")]
                for dep_name in dep_names:
                    if dep_name and dep_name in task_ids:
                        dependencies.append(task_ids[dep_name])
            
            task = {
                "id": task_ids[row["Tâche"]],
                "name": row["Tâche"],
                "start_date": row["Date de début"].date().isoformat(),
                "end_date": row["Date de fin"].date().isoformat(),
                "resource": row["Responsable"],
                "status": row["Statut"],
                "priority": row["Priorité"],
                "dependencies": dependencies,
                "description": row["Description"]
            }
            
            project["tasks"].append(task)
        
        # Sauvegarder le projet
        self.save_project(project)
        
        return project
    
    def export_project_to_csv(self, project):
        """
        Exporte un projet au format CSV
        
        Args:
            project (dict): Projet à exporter
            
        Returns:
            str: Contenu CSV
        """
        df = self.project_to_dataframe(project)
        if not df.empty:
            # Supprimer la colonne ID qui est interne
            if "ID" in df.columns:
                df = df.drop(columns=["ID"])
            
            return df.to_csv(index=False)
        
        return ""