import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from utils.geometry_component import geometry_editor
    from utils.nav import render_sidebar
    from utils.interactive_viewer import render_interactive_graph
    from utils.shape_math import Shape, get_screen_vertices, sync_shape_position, generate_full_svg
except ImportError as e:
    st.error(f"Setup Error: {e}")
    st.stop()

st.set_page_config(layout="wide", page_title="Shape Builder")
render_sidebar()

# --- CSS ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; }
        div[data-testid="column"] { padding: 0px; }
    </style>
""", unsafe_allow_html=True)

st.title("📐 Geometry Shape Builder")

# --- INITIALIZATION ---
if 'shapes' not in st.session_state:
    st.session_state.shapes = []
if 'next_id' not in st.session_state:
    st.session_state.next_id = 0

# --- CANVAS SETTINGS ---
with st.sidebar.expander("Canvas Settings", expanded=True):
    w_cm = st.number_input("Width (cm)", 5.0, 50.0, 20.0)
    h_cm = st.number_input("Height (cm)", 5.0, 50.0, 14.0)

    # NEW: Editor Zoom Slider
    # This scales the pixels but keeps the math units (cm) the same
    editor_zoom = st.slider("Editor Zoom", 0.5, 2.5, 1.0, step=0.1)

    show_grid = st.checkbox("Show Grid", True)

# Apply Zoom to the Pixel Calculations
w_px = w_cm * 28.35 * editor_zoom
h_px = h_cm * 28.35 * editor_zoom
cx, cy = w_px / 2, h_px / 2
scale = 30.0 * editor_zoom  # Scale the content match

# --- ADD SHAPE ---
st.sidebar.subheader("1. Create")
c1, c2 = st.sidebar.columns(2)
s_type = c1.selectbox("Type", ["Rectangle", "Square", "Triangle"], label_visibility="collapsed")
if st.sidebar.button("Add Shape"):
    st.session_state.shapes.append(Shape(
        id=st.session_state.next_id, type=s_type, params={}, color="#FFFFFF"
    ))
    st.session_state.next_id += 1

# --- MAIN LAYOUT ---
col_props, col_canvas = st.columns([1, 3])

# 1. PROPERTY EDITOR (STABLE FORM)
with col_props:
    st.write("### 2. Edit Properties")
    if not st.session_state.shapes:
        st.info("Add a shape to begin.")
    else:
        with st.form("shape_properties"):
            st.write("Modify selected shapes below:")

            # We track if a nudge button was pressed
            nudge_action = None

            for s in st.session_state.shapes:
                st.markdown(f"**Shape {s.id}: {s.type}**")

                # Dimensions
                c1, c2 = st.columns(2)
                curr_w = s.params.get('w', s.params.get('base', s.params.get('s', 4.0)))
                curr_h = s.params.get('h', s.params.get('height', 3.0))

                new_w = c1.number_input("W/Base", 0.1, 20.0, float(curr_w), key=f"w_{s.id}")
                if s.type != "Square":
                    new_h = c2.number_input("Height", 0.1, 20.0, float(curr_h), key=f"h_{s.id}")

                # Appearance
                c3, c4 = st.columns(2)
                new_color = c3.color_picker("Color", s.color, key=f"c_{s.id}")
                new_rot = c4.number_input("Rot", -180, 180, int(s.rotation), key=f"r_{s.id}")

                # Label & Toggles
                new_label = st.text_input("Label (supports math)", s.center_label, key=f"l_{s.id}")
                c5, c6 = st.columns(2)
                show_v = c5.checkbox("Vertices", s.show_vertices, key=f"sv_{s.id}")
                show_l = c6.checkbox("Label", s.show_label, key=f"sl_{s.id}")

                # NUDGE CONTROLS (New)
                st.caption("Fine Adjustment")
                n1, n2, n3, n4 = st.columns(4)
                if n1.form_submit_button(f"⬅️", type="secondary"): nudge_action = (s.id, -0.1, 0)
                if n2.form_submit_button(f"➡️", type="secondary"): nudge_action = (s.id, 0.1, 0)
                if n3.form_submit_button(f"⬆️", type="secondary"): nudge_action = (s.id, 0, 0.1)
                if n4.form_submit_button(f"⬇️", type="secondary"): nudge_action = (s.id, 0, -0.1)

                # Delete
                st.checkbox("Delete", key=f"del_{s.id}")
                st.divider()

            submitted = st.form_submit_button("Update Properties", type="primary")

            # Logic to handle updates (runs if "Update" OR any "Nudge" is clicked)
            if submitted or nudge_action:
                ids_to_remove = []
                for s in st.session_state.shapes:
                    # 1. Apply Nudge if applicable
                    if nudge_action and s.id == nudge_action[0]:
                        s.x += nudge_action[1]
                        s.y += nudge_action[2]

                    # 2. Check Delete
                    if st.session_state.get(f"del_{s.id}", False):
                        ids_to_remove.append(s.id)
                        continue

                    # 3. Save Form Inputs
                    s.color = st.session_state[f"c_{s.id}"]
                    s.rotation = st.session_state[f"r_{s.id}"]
                    s.center_label = st.session_state[f"l_{s.id}"]
                    s.show_vertices = st.session_state[f"sv_{s.id}"]
                    s.show_label = st.session_state[f"sl_{s.id}"]

                    if s.type == "Rectangle":
                        s.params['w'] = st.session_state[f"w_{s.id}"]
                        s.params['h'] = st.session_state[f"h_{s.id}"]
                    elif s.type == "Triangle":
                        s.params['base'] = st.session_state[f"w_{s.id}"]
                        s.params['height'] = st.session_state[f"h_{s.id}"]
                    elif s.type == "Square":
                        s.params['s'] = st.session_state[f"w_{s.id}"]

                st.session_state.shapes = [s for s in st.session_state.shapes if s.id not in ids_to_remove]
                st.rerun()

# 2. INTERACTIVE EDITOR
with col_canvas:
    # Build JS Data
    js_shapes = []
    for s in st.session_state.shapes:
        pts = get_screen_vertices(s, cx, cy, scale)
        js_pts = [{'x': p[0], 'y': p[1]} for p in pts]
        display_label = s.center_label if s.show_label else ""

        js_shapes.append({
            'id': s.id,
            'points': js_pts,
            'color': s.color,
            'stroke': s.stroke,
            'stroke_width': s.stroke_width,
            'label': display_label,
            'show_vertices': s.show_vertices
        })

    # We update the KEY with zoom level to force a full redraw when zooming
    returned_shapes = geometry_editor(
        js_shapes, w_px, h_px, show_grid=show_grid, key=f"geo_{w_px}_{editor_zoom}"
    )

    # Sync Drag
    if returned_shapes:
        changes = False
        for js_s in returned_shapes:
            if sync_shape_position(js_s, st.session_state.shapes, scale, cx, cy):
                changes = True
        if changes:
            st.rerun()

# 3. FINAL OUTPUT (WITH CROP TOOL)
st.markdown("---")
st.header("3. Final Preview & Export")
st.write("Use the tools below to Crop, Zoom, and Download your graph.")

if st.session_state.shapes:
    svg_string = generate_full_svg(st.session_state.shapes, w_cm, h_cm)
    render_interactive_graph(
        svg_string,
        w_px, h_px,  # Use the zoomed dimensions for the preview container
        w_cm, h_cm,
        scale_choice=1
    )