import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Load the interaction matrix, unique_senator_ids, and senator_id_to_index from JSON
with open("./data/parliament/senate_interaction_matrix.json", 'r') as f:
    interaction_matrix = json.load(f)

with open("./data/parliament/unique_senator_ids.json", 'r') as f:
    unique_senator_ids = set(json.load(f))

with open("./data/parliament/senate.json", 'r') as f:
    senators_data = json.load(f)

# Convert it back to a NumPy array for easier manipulation
interaction_matrix = np.array(interaction_matrix)

# Create a mapping from senator ID to party
senator_id_to_party = {senator['id']: senator['effective_party'] for senator in senators_data}

# Define the party color map
party_color_map = {
    'Australian Greens': '#009C3D',
    'Australian Labor Party': '#E13940',
    'David Pocock': '#4ef8a6',
    'Lidia Thorpe': '#7A3535',
    'Jacqui Lambie Network': '#FFFFFF',
    'Liberal National Party': '#1C4F9C',
    'Pauline Hanson\'s One Nation Party': '#F36D24',
    'United Australia Party': '#ffed00'
}

# Create nodes using the Node class from streamlit-agraph
nodes = []
for i, senator_id in enumerate(list(unique_senator_ids)):
    party = senator_id_to_party.get(senator_id, 'Unknown')  # Get the party or 'Unknown' if not found
    color = party_color_map.get(party, '#000000')  # Get the color or default to black
    nodes.append(Node(id=str(i), label=str(senator_id), color=color))

# Create edges
edges = []
for i in range(len(interaction_matrix)):
    for j in range(i+1, len(interaction_matrix)):
        weight = interaction_matrix[i][j]
        if weight > 0:  # Only add an edge if there's a non-zero interaction
            edges.append(Edge(source=str(i), target=str(j), weight=weight))

# Create a Config object with physics options
config = Config(
    width=800,
    height=600,
    directed=False,
    physics={
        "barnesHut": {
            "gravitationalConstant": -30000,
            "centralGravity": 0.3,
            "springLength": 95,
            "springConstant": 0.04,
            "damping": 0.09,
            "avoidOverlap": 0.1
        }
    }
)

# Display the graph using agraph
return_value = agraph(nodes=nodes, edges=edges, config=config)

