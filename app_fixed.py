import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import uuid

from data_manager import DataManager
# Importer la nouvelle classe corrigée au lieu de l'originale
from gantt_visualizer_fixed import GanttVisualizer
from utils import validate_excel_file, generate_example_excel, calculate_project_stats

# Configuration de la page
st.set_page_config(
    page_title="Gantt Planner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des classes principales
data_manager = DataManager()
gantt_visualizer = GanttVisualizer()

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .status-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f9f9f9;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 0.2rem;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de l'état de session
if "projects" not in st.session_state:
    st.session_state.projects = data_manager.load_all_projects()
if "current_project" not in st.session_state:
    st.session_state.current_project = None
if "show_task_form" not in st.session_state:
    st.session_state.show_task_form = False
if "edit_task_id" not in st.session_state:
    st.session_state.edit_task_id = None

# Fonctions de callback
def create_new_project():
    """Crée un nouveau projet vide"""
    st.session_state.current_project = {
        "id": str(uuid.uuid4()),
        "name": "Nouveau projet",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tasks": []
    }
    data_manager.save_project(st.session_state.current_project)
    st.session_state.projects = data_manager.load_all_projects()

def load_project(project_id):
    """Charge un projet existant"""
    st.session_state.current_project = data_manager.load_project(project_id)
    st.session_state.show_task_form = False
    st.session_state.edit_task_id = None

def duplicate_project():
    """Duplique le projet actuel"""
    if st.session_state.current_project:
        new_project = st.session_state.current_project.copy()
        new_project["id"] = str(uuid.uuid4())
        new_project["name"] = f"{new_project['name']} (copie)"
        new_project["created_at"] = datetime.now().isoformat()
        new_project["updated_at"] = datetime.now().isoformat()
        
        # Générer de nouveaux IDs pour les tâches
        old_to_new_ids = {}
        for task in new_project["tasks"]:
            old_id = task["id"]
            new_id = f"task-{str(uuid.uuid4())[:8]}"
            old_to_new_ids[old_id] = new_id
            task["id"] = new_id
        
        # Mettre à jour les dépendances
        for task in new_project["tasks"]:
            updated_deps = []
            for dep_id in task["dependencies"]:
                if dep_id in old_to_new_ids:
                    updated_deps.append(old_to_new_ids[dep_id])
            task["dependencies"] = updated_deps
        
        data_manager.save_project(new_project)
        st.session_state.projects = data_manager.load_all_projects()
        st.session_state.current_project = new_project

def toggle_task_form():
    """Affiche ou masque le formulaire d'ajout/édition de tâche"""
    st.session_state.show_task_form = not st.session_state.show_task_form
    st.session_state.edit_task_id = None

def edit_task(task_id):
    """Permet l'édition d'une tâche existante"""
    st.session_state.edit_task_id = task_id
    st.session_state.show_task_form = True

def delete_task(task_id):
    """Supprime une tâche du projet actuel"""
    if st.session_state.current_project:
        st.session_state.current_project["tasks"] = [
            task for task in st.session_state.current_project["tasks"] 
            if task["id"] != task_id
        ]
        st.session_state.current_project["updated_at"] = datetime.now().isoformat()
        data_manager.save_project(st.session_state.current_project)

def delete_project(project_id):
    """Supprime un projet"""
    data_manager.delete_project(project_id)
    st.session_state.projects = data_manager.load_all_projects()
    if st.session_state.current_project and st.session_state.current_project["id"] == project_id:
        st.session_state.current_project = None

# Interface utilisateur principale
def main():
    # Sidebar pour la navigation et la gestion des projets
    with st.sidebar:
        st.title("📊 Gantt Planner")
        
        st.button("➕ Nouveau projet", on_click=create_new_project, use_container_width=True)
        
        if st.session_state.projects:
            st.subheader("Projets existants")
            for project in st.session_state.projects:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    if st.button(project["name"], key=f"load_{project['id']}", use_container_width=True):
                        load_project(project["id"])
                with col2:
                    if st.button("🗑️", key=f"delete_{project['id']}", help="Supprimer ce projet"):
                        delete_project(project["id"])
                with col3:
                    if st.button("📋", key=f"duplicate_{project['id']}", help="Dupliquer ce projet"):
                        st.session_state.current_project = data_manager.load_project(project["id"])
                        duplicate_project()
        
        st.divider()
        
        with st.expander("📤 Importer un projet"):
            uploaded_file = st.file_uploader("Choisir un fichier Excel", type=["xlsx"])
            
            if uploaded_file:
                try:
                    # Valider et traiter le fichier
                    df = pd.read_excel(uploaded_file)
                    is_valid, message = validate_excel_file(df)
                    
                    if is_valid:
                        with st.form("import_form"):
                            project_name = st.text_input("Nom du projet", value=f"Projet importé {datetime.now().strftime('%d/%m/%Y')}")
                            submit_button = st.form_submit_button("Importer")
                            
                            if submit_button:
                                new_project = data_manager.create_project_from_dataframe(df, project_name)
                                st.session_state.projects = data_manager.load_all_projects()
                                st.session_state.current_project = new_project
                                st.success("Projet importé avec succès !")
                    else:
                        st.error(f"Erreur dans le fichier : {message}")
                except Exception as e:
                    st.error(f"Erreur lors de l'importation : {str(e)}")
        
        with st.expander("📥 Télécharger un exemple"):
            if st.button("Télécharger le modèle Excel"):
                example_df = generate_example_excel()
                st.download_button(
                    label="📥 Télécharger",
                    data=example_df,
                    file_name="gantt_planner_modele.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # Contenu principal
    if st.session_state.current_project:
        project = st.session_state.current_project
        
        # En-tête du projet
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            project_name = st.text_input("Nom du projet", value=project["name"])
            if project_name != project["name"]:
                project["name"] = project_name
                project["updated_at"] = datetime.now().isoformat()
                data_manager.save_project(project)
        
        with col2:
            if st.button("📋 Dupliquer ce projet", use_container_width=True):
                duplicate_project()
        
        with col3:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.experimental_rerun()
        
        # Tableau récapitulatif
        tasks_df = data_manager.project_to_dataframe(project)
        
        if not tasks_df.empty:
            # Métriques
            stats = calculate_project_stats(tasks_df)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total des tâches", stats["total_tasks"])
            with col2:
                st.metric("Tâches terminées", f"{stats['completed_tasks']} ({stats['completion_rate']:.1f}%)")
            with col3:
                st.metric("Tâches critiques", stats["critical_tasks"])
            with col4:
                st.metric("Durée (jours)", stats["duration"])
            
            # Filtres
            with st.expander("🔍 Filtres", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    status_filter = st.multiselect(
                        "Statut",
                        options=tasks_df["Statut"].unique(),
                        default=tasks_df["Statut"].unique()
                    )
                
                with col2:
                    resource_filter = st.multiselect(
                        "Responsable",
                        options=tasks_df["Responsable"].unique(),
                        default=tasks_df["Responsable"].unique()
                    )
                
                with col3:
                    priority_filter = st.multiselect(
                        "Priorité",
                        options=tasks_df["Priorité"].unique(),
                        default=tasks_df["Priorité"].unique()
                    )
                
                with col4:
                    min_date = tasks_df["Date de début"].min()
                    max_date = tasks_df["Date de fin"].max()
                    date_range = st.date_input(
                        "Période",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
            
            # Appliquer les filtres
            filtered_df = tasks_df[
                tasks_df["Statut"].isin(status_filter) &
                tasks_df["Responsable"].isin(resource_filter) &
                tasks_df["Priorité"].isin(priority_filter)
            ]
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (filtered_df["Date de début"] >= pd.Timestamp(start_date)) &
                    (filtered_df["Date de fin"] <= pd.Timestamp(end_date))
                ]
            
            # Visualisation et tableau
            tab1, tab2 = st.tabs(["📊 Diagramme de Gantt", "📋 Tableau des tâches"])
            
            with tab1:
                if not filtered_df.empty:
                    # Options de visualisation
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        color_by = st.selectbox(
                            "Colorer par",
                            options=["Statut", "Responsable", "Priorité"]
                        )
                    with col2:
                        sort_by = st.selectbox(
                            "Trier par",
                            options=["Date de début", "Date de fin", "Durée", "Responsable", "Priorité"]
                        )
                    with col3:
                        show_critical = st.checkbox("Mettre en évidence les tâches critiques", value=True)
                    
                    # Créer et afficher le diagramme de Gantt
                    fig = gantt_visualizer.create_gantt_chart(
                        filtered_df, 
                        color_by=color_by, 
                        sort_by=sort_by,
                        highlight_critical=show_critical
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Export
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📥 Exporter en PNG", use_container_width=True):
                            img_bytes = gantt_visualizer.export_gantt_as_image(fig)
                            st.download_button(
                                label="📥 Télécharger PNG",
                                data=img_bytes,
                                file_name=f"{project['name']}_gantt.png",
                                mime="image/png"
                            )
                    with col2:
                        if st.button("📥 Exporter en CSV", use_container_width=True):
                            csv = filtered_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Télécharger CSV",
                                data=csv,
                                file_name=f"{project['name']}_tasks.csv",
                                mime="text/csv"
                            )
                else:
                    st.info("Aucune tâche ne correspond aux filtres sélectionnés.")
            
            with tab2:
                if not filtered_df.empty:
                    editable_df = st.data_editor(
                        filtered_df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Date de début": st.column_config.DateColumn(
                                "Date de début",
                                format="DD/MM/YYYY"
                            ),
                            "Date de fin": st.column_config.DateColumn(
                                "Date de fin",
                                format="DD/MM/YYYY"
                            ),
                            "Statut": st.column_config.SelectboxColumn(
                                "Statut",
                                options=["Non démarré", "En cours", "Terminé", "En retard"]
                            ),
                            "Priorité": st.column_config.SelectboxColumn(
                                "Priorité",
                                options=["Basse", "Moyenne", "Haute", "Critique"]
                            )
                        }
                    )
                    
                    # Détection des modifications dans le tableau
                    if not editable_df.equals(filtered_df):
                        if st.button("💾 Enregistrer les modifications", use_container_width=True):
                            # Mettre à jour les tâches dans le projet
                            data_manager.update_tasks_from_dataframe(project, editable_df)
                            st.session_state.current_project = project
                            st.success("Modifications enregistrées !")
                            st.experimental_rerun()
                else:
                    st.info("Aucune tâche ne correspond aux filtres sélectionnés.")
        
        # Formulaire d'ajout/édition de tâche
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("➕ Nouvelle tâche", use_container_width=True):
                toggle_task_form()
        
        if st.session_state.show_task_form:
            with st.form("task_form"):
                st.subheader("Détails de la tâche")
                
                # Récupérer la tâche en édition si elle existe
                edit_task_data = None
                if st.session_state.edit_task_id:
                    for task in project["tasks"]:
                        if task["id"] == st.session_state.edit_task_id:
                            edit_task_data = task
                            break
                
                col1, col2 = st.columns(2)
                with col1:
                    task_name = st.text_input(
                        "Nom de la tâche", 
                        value=edit_task_data["name"] if edit_task_data else ""
                    )
                with col2:
                    task_resource = st.text_input(
                        "Responsable", 
                        value=edit_task_data["resource"] if edit_task_data else ""
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    if edit_task_data:
                        start_date = pd.to_datetime(edit_task_data["start_date"]).date()
                    else:
                        # Utiliser la date actuelle comme date de début par défaut
                        # Si le projet a des tâches, utiliser la date de fin du projet comme référence minimale
                        if not tasks_df.empty:
                            min_start_date = tasks_df["Date de début"].min().date()
                            today = datetime.now().date()
                            # Prendre le max entre aujourd'hui et la date minimale du projet
                            start_date = max(today, min_start_date)
                        else:
                            start_date = datetime.now().date()
                    
                    task_start_date = st.date_input(
                        "Date de début",
                        value=start_date
                    )
                
                with col2:
                    if edit_task_data:
                        end_date = pd.to_datetime(edit_task_data["end_date"]).date()
                    else:
                        # Ajouter 1 semaine à la date de début par défaut
                        end_date = task_start_date + timedelta(days=7)
                    
                    task_end_date = st.date_input(
                        "Date de fin",
                        value=end_date,
                        min_value=task_start_date
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    task_status = st.selectbox(
                        "Statut",
                        options=["Non démarré", "En cours", "Terminé", "En retard"],
                        index=0 if not edit_task_data else ["Non démarré", "En cours", "Terminé", "En retard"].index(edit_task_data["status"])
                    )
                
                with col2:
                    task_priority = st.selectbox(
                        "Priorité",
                        options=["Basse", "Moyenne", "Haute", "Critique"],
                        index=1 if not edit_task_data else ["Basse", "Moyenne", "Haute", "Critique"].index(edit_task_data["priority"])
                    )
                
                # Dépendances
                if not tasks_df.empty:
                    available_tasks = tasks_df["Tâche"].tolist()
                    
                    # Exclure la tâche actuelle des dépendances possibles
                    if edit_task_data:
                        if edit_task_data["name"] in available_tasks:
                            available_tasks.remove(edit_task_data["name"])
                    
                    default_deps = []
                    if edit_task_data:
                        # Convertir les IDs de dépendance en noms de tâches
                        for dep_id in edit_task_data["dependencies"]:
                            for task in project["tasks"]:
                                if task["id"] == dep_id and task["name"] in available_tasks:
                                    default_deps.append(task["name"])
                    
                    task_dependencies = st.multiselect(
                        "Dépendances",
                        options=available_tasks,
                        default=default_deps
                    )
                else:
                    task_dependencies = []
                
                task_description = st.text_area(
                    "Description",
                    value=edit_task_data["description"] if edit_task_data else "",
                    height=100
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_button = st.form_submit_button(
                        "Enregistrer" if edit_task_data else "Ajouter",
                        use_container_width=True
                    )
                with col2:
                    cancel_button = st.form_submit_button(
                        "Annuler",
                        use_container_width=True
                    )
                
                if submit_button:
                    # Convertir les noms de tâches dépendantes en IDs
                    dependency_ids = []
                    for dep_name in task_dependencies:
                        for task in project["tasks"]:
                            if task["name"] == dep_name:
                                dependency_ids.append(task["id"])
                                break
                    
                    if edit_task_data:
                        # Mise à jour d'une tâche existante
                        for task in project["tasks"]:
                            if task["id"] == st.session_state.edit_task_id:
                                task["name"] = task_name
                                task["start_date"] = task_start_date.isoformat()
                                task["end_date"] = task_end_date.isoformat()
                                task["resource"] = task_resource
                                task["status"] = task_status
                                task["priority"] = task_priority
                                task["dependencies"] = dependency_ids
                                task["description"] = task_description
                                break
                    else:
                        # Création d'une nouvelle tâche
                        new_task = {
                            "id": f"task-{str(uuid.uuid4())[:8]}",
                            "name": task_name,
                            "start_date": task_start_date.isoformat(),
                            "end_date": task_end_date.isoformat(),
                            "resource": task_resource,
                            "status": task_status,
                            "priority": task_priority,
                            "dependencies": dependency_ids,
                            "description": task_description
                        }
                        project["tasks"].append(new_task)
                    
                    project["updated_at"] = datetime.now().isoformat()
                    data_manager.save_project(project)
                    
                    st.session_state.show_task_form = False
                    st.session_state.edit_task_id = None
                    st.experimental_rerun()
                
                if cancel_button:
                    st.session_state.show_task_form = False
                    st.session_state.edit_task_id = None
                    st.experimental_rerun()
    
    else:
        # Page d'accueil si aucun projet n'est sélectionné
        st.markdown("<h1 class='main-header'>📊 Gantt Planner</h1>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
            <h2>Bienvenue dans Gantt Planner</h2>
            <p>Cette application vous permet de gérer vos projets sous forme de diagrammes de Gantt interactifs.</p>
            <p>Pour commencer, vous pouvez :</p>
            <ul>
                <li>Créer un nouveau projet</li>
                <li>Importer un projet depuis un fichier Excel</li>
                <li>Charger un projet existant depuis la barre latérale</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<h3>Créer un nouveau projet</h3>", unsafe_allow_html=True)
            if st.button("➕ Nouveau projet", key="home_new_project", use_container_width=True):
                create_new_project()
                st.experimental_rerun()
        
        with col2:
            st.markdown("<h3>Importer depuis Excel</h3>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Choisir un fichier Excel", key="home_upload", type=["xlsx"])
            
            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)
                    is_valid, message = validate_excel_file(df)
                    
                    if is_valid:
                        with st.form("home_import_form"):
                            project_name = st.text_input("Nom du projet", value=f"Projet importé {datetime.now().strftime('%d/%m/%Y')}")
                            submit_button = st.form_submit_button("Importer")
                            
                            if submit_button:
                                new_project = data_manager.create_project_from_dataframe(df, project_name)
                                st.session_state.projects = data_manager.load_all_projects()
                                st.session_state.current_project = new_project
                                st.success("Projet importé avec succès !")
                                st.experimental_rerun()
                    else:
                        st.error(f"Erreur dans le fichier : {message}")
                except Exception as e:
                    st.error(f"Erreur lors de l'importation : {str(e)}")

if __name__ == "__main__":
    main()