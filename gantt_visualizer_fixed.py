import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta

class GanttVisualizer:
    def __init__(self):
        # Palettes de couleurs pour différents attributs
        self.status_colors = {
            "Non démarré": "#9E9E9E",  # Gris
            "En cours": "#2196F3",     # Bleu
            "Terminé": "#4CAF50",      # Vert
            "En retard": "#F44336"     # Rouge
        }
        
        self.priority_colors = {
            "Basse": "#81C784",       # Vert clair
            "Moyenne": "#FFB74D",     # Orange clair
            "Haute": "#FF8A65",       # Orange foncé
            "Critique": "#E57373"     # Rouge clair
        }
    
    def create_gantt_chart(self, df, color_by="Statut", sort_by="Date de début", highlight_critical=True):
        """
        Crée un diagramme de Gantt interactif avec Plotly
        
        Args:
            df (pandas.DataFrame): DataFrame contenant les données des tâches
            color_by (str): Attribut à utiliser pour la couleur
            sort_by (str): Attribut à utiliser pour le tri
            highlight_critical (bool): Si True, met en évidence les tâches critiques
            
        Returns:
            plotly.graph_objects.Figure: Diagramme de Gantt
        """
        if df.empty:
            # Retourner une figure vide si aucune donnée
            return go.Figure()
        
        # Copie pour éviter de modifier le DataFrame d'origine
        df_copy = df.copy()
        
        # Traitement des dates pour s'assurer qu'elles sont au format datetime
        for col in ["Date de début", "Date de fin"]:
            if df_copy[col].dtype != 'datetime64[ns]':
                df_copy[col] = pd.to_datetime(df_copy[col])
        
        # Tri des données
        if sort_by == "Durée":
            # Calculer la durée si ce n'est pas déjà fait
            if "Durée" not in df_copy.columns:
                df_copy["Durée"] = (df_copy["Date de fin"] - df_copy["Date de début"]).dt.days + 1
            df_copy = df_copy.sort_values("Durée", ascending=False)
        else:
            df_copy = df_copy.sort_values(sort_by)
        
        # Définir les couleurs en fonction de l'attribut choisi
        if color_by == "Statut":
            color_map = self.status_colors
        elif color_by == "Priorité":
            color_map = self.priority_colors
        else:
            # Pour les ressources, générer une palette de couleurs
            unique_resources = df_copy["Responsable"].unique()
            colors = px.colors.qualitative.Plotly[:len(unique_resources)]
            color_map = {resource: color for resource, color in zip(unique_resources, colors)}
        
        # Créer le diagramme de base
        fig = px.timeline(
            df_copy,
            x_start="Date de début",
            x_end="Date de fin",
            y="Tâche",
            color=color_by,
            color_discrete_map=color_map,
            hover_data=["Responsable", "Statut", "Priorité", "Description"],
            labels={
                "Tâche": "Tâche",
                "Date de début": "Date de début",
                "Date de fin": "Date de fin",
                "Responsable": "Responsable",
                "Statut": "Statut",
                "Priorité": "Priorité"
            }
        )
        
        # Mise en forme spécifique pour les tâches critiques
        if highlight_critical and "Priorité" in df_copy.columns:
            critical_tasks = df_copy[df_copy["Priorité"] == "Critique"]
            if not critical_tasks.empty:
                # Ajouter un contour pour les tâches critiques
                for idx, task in critical_tasks.iterrows():
                    fig.add_shape(
                        type="rect",
                        x0=task["Date de début"],
                        x1=task["Date de fin"],
                        y0=task["Tâche"],
                        y1=task["Tâche"],
                        line=dict(
                            color="#B71C1C",
                            width=2
                        ),
                        fillcolor="rgba(0,0,0,0)",
                        layer="below"
                    )
        
        # Personnalisation du layout
        fig.update_layout(
            title="Diagramme de Gantt",
            xaxis_title="Dates",
            yaxis_title="Tâches",
            height=max(600, len(df_copy) * 40),  # Hauteur dynamique selon le nombre de tâches
            xaxis=dict(
                type='date',
                tickformat='%d/%m/%Y',
                title_font=dict(size=14),
                rangeslider_visible=True
            ),
            yaxis=dict(
                autorange="reversed",  # Inverser l'axe Y pour avoir la première tâche en haut
                title_font=dict(size=14)
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12
            ),
            margin=dict(l=60, r=40, t=80, b=60)
        )
        
        # Utiliser add_shape au lieu de add_vline pour éviter les problèmes de Timestamp
        today = datetime.now().date()
        
        fig.add_shape(
            type="line",
            x0=today,
            y0=0,
            x1=today,
            y1=1,
            yref="paper",
            line=dict(
                color="black",
                width=2,
                dash="dash"
            )
        )
        
        # Ajouter l'annotation "Aujourd'hui" séparément
        fig.add_annotation(
            x=today,
            y=1.02,
            yref="paper",
            text="Aujourd'hui",
            showarrow=False,
            font=dict(
                size=12,
                color="black"
            )
        )
        
        return fig
    
    def export_gantt_as_image(self, fig):
        """
        Exporte le diagramme de Gantt en image PNG
        
        Args:
            fig (plotly.graph_objects.Figure): Diagramme de Gantt à exporter
            
        Returns:
            bytes: Image au format PNG
        """
        img_bytes = fig.to_image(format="png", width=1200, height=800, scale=2)
        return img_bytes