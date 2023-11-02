import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os

# Load the interaction matrix, unique_senator_ids, and senator_id_to_index from JSON
with open("./data/parliament/senate_interaction_matrix.json", 'r') as f:
    interaction_matrix = json.load(f)

with open("./data/parliament/unique_senator_ids.json", 'r') as f:
    d_unique_senators = set(json.load(f))

with open("./data/parliament/senate.json", 'r') as f:
    senators_data = json.load(f)

def load_divisions_from_files():
    # Define the directory and filename
    directory = './data/parliament'
    filename = f"{directory}/divisions.json"
    
    # Check if the file with all divisions exists
    if os.path.exists(filename):
        # Load data from the file if it exists
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        #st.write("No local division data found.")
        return None

divisions = load_divisions_from_files()
senate_divisions = {}
for division_id, division_data in divisions.items():
    if division_data['house'] == 'senate':
        senate_divisions[division_id] = division_data

# Determine the number of unique senators (d) and divisions (L)
d = len(d_unique_senators)
L = len(senate_divisions)

# Initialize a tensor to hold the training data
# Shape: [d, d, L]
training_data = np.zeros((d, d, L))

# Create a mapping from senator IDs to tensor indices
senator_id_to_index = {senator_id: index for index, senator_id in enumerate(d_unique_senators)}

# Iterate through each division to populate the training data
for l, (division_id, division_data) in enumerate(senate_divisions.items()):
    # Create a dictionary to hold the votes for this division, analogous to vector 'X' in the paper
    X = {}
    st.write(division_data['name'])
    for vote_data in division_data['votes']:
        senator_id = vote_data['member']['id']
        vote = 1 if vote_data['vote'] == 'aye' else -1  # Assuming 'aye' is +1 and 'no' is -1
        X[senator_id] = vote
    
    # Update the training_data tensor, analogous to creating samples to estimate 'M' in the paper
    for i, senator_id_i in enumerate(d_unique_senators):
        for j, senator_id_j in enumerate(d_unique_senators):
            if senator_id_i in X and senator_id_j in X:
                training_data[i, j, l] = X[senator_id_i] * X[senator_id_j]
    st.write(training_data[:,:,0])

st.write(training_data[:,:,0])

# --------- Network Vis -----------
# # Convert it back to a NumPy array for easier manipulation
# interaction_matrix = np.array(interaction_matrix)

# # Create a mapping from senator ID to party
# senator_id_to_party = {senator['id']: senator['effective_party'] for senator in senators_data}

# # Define the party color map
# party_color_map = {
#     'Australian Greens': '#009C3D',
#     'Australian Labor Party': '#E13940',
#     'David Pocock': '#4ef8a6',
#     'Lidia Thorpe': '#7A3535',
#     'Jacqui Lambie Network': '#FFFFFF',
#     'Liberal National Party': '#1C4F9C',
#     'Pauline Hanson\'s One Nation Party': '#F36D24',
#     'United Australia Party': '#ffed00'
# }

# # Create nodes using the Node class from streamlit-agraph
# nodes = []
# for i, senator_id in enumerate(list(unique_senator_ids)):
#     party = senator_id_to_party.get(senator_id, 'Unknown')  # Get the party or 'Unknown' if not found
#     color = party_color_map.get(party, '#000000')  # Get the color or default to black
#     nodes.append(Node(id=str(i), label=str(senator_id), color=color))

# # Create edges
# edges = []
# for i in range(len(interaction_matrix)):
#     for j in range(i+1, len(interaction_matrix)):
#         weight = interaction_matrix[i][j]
#         if weight > 0:  # Only add an edge if there's a non-zero interaction
#             edges.append(Edge(source=str(i), target=str(j), weight=weight))

# # Create a Config object with physics options
# config = Config(
#     width=800,
#     height=600,
#     directed=False,
#     physics={
#         "barnesHut": {
#             "gravitationalConstant": -30000,
#             "centralGravity": 0.3,
#             "springLength": 95,
#             "springConstant": 0.04,
#             "damping": 0.09,
#             "avoidOverlap": 0.1
#         }
#     }
# )

# Display the graph using agraph
#return_value = agraph(nodes=nodes, edges=edges, config=config)

