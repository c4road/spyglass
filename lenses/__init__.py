"""SpyGlass lenses.

Each lens is a self-contained Streamlit app in its own subpackage, with its own
``app.py`` entry point — there is no shared router or registry. Shared, pure
logic lives in the repo-root ``core/`` package.

    streamlit run lenses/position_sizer/app.py
"""
