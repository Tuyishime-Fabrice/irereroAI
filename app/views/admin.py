"""Admin: users and roles, data files and rebuild. Admins cannot change plan decisions."""

from html import escape

import streamlit as st

from irerero import audit
from irerero.config import INTERIM, RAW
from irerero.data.registry import FILE_DATASETS
from irerero.db.models import AppUser
from irerero.ui import data, theme
from irerero.ui.roles import ROLE_LABELS, current
from irerero.ui.theme import Col

user = current()
eng = data.eng()
theme.header(
    "Admin",
    "Users and roles, data files. Plan decisions are not editable here.",
    crumbs=["Rwanda", "Admin"],
    assistant="admin",
)

with theme.panel("Users", "Fictional demo accounts and their roles", "users"):
    users = data.table("app_user")
    st.dataframe(
        users.assign(role=users.role.map(ROLE_LABELS)).rename(
            columns={
                "user_id": "User",
                "role": "Role",
                "name": "Name",
                "district_id": "District",
                "sector_id": "Sector",
                "centre_id": "Centre",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    with st.form("role", border=False):
        st.markdown("**Change a user's role or area** (recorded in the audit log)")
        c1, c2, c3, c4 = st.columns(4)
        who = c1.selectbox("User", users.user_id.tolist())
        role = c2.selectbox("Role", list(ROLE_LABELS), format_func=ROLE_LABELS.get)
        district = c3.text_input("District id", "")
        sector = c4.text_input("Sector id", "")
        if st.form_submit_button("Save"):
            from sqlalchemy.orm import Session

            with Session(eng) as s:
                row = s.get(AppUser, who)
                before = {
                    "role": row.role,
                    "district_id": row.district_id,
                    "sector_id": row.sector_id,
                }
                row.role = role
                row.district_id = district or row.district_id
                row.sector_id = sector or row.sector_id
                audit.write(
                    s,
                    user,
                    "user.update",
                    "app_user",
                    who,
                    before=before,
                    after={
                        "role": row.role,
                        "district_id": row.district_id,
                        "sector_id": row.sector_id,
                    },
                )
                s.commit()
            data.clear()
            st.rerun()
    theme.note("Demo users are fictional. The demo role picker uses its own fixed demo accounts.")

with theme.panel(
    "Data files",
    "One folder per dataset under data/raw/. Add received files with "
    "python -m irerero.data.intake; it writes data/interim/intake_report.md.",
    "database",
):
    st.markdown(
        theme.table(
            [
                {
                    "dataset": d.title,
                    "folder": f"data/raw/{d.key}/",
                    "files": ", ".join(d.files),
                    "present": d.present(RAW),
                    "received": any((INTERIM / d.key).glob("*")),
                }
                for d in FILE_DATASETS
            ],
            [
                Col("dataset", "Dataset", strong=True),
                Col("folder", "Folder", fmt=lambda v, r: f"<code>{escape(v)}</code>"),
                Col(
                    "files",
                    "Expected files",
                    fmt=lambda v, r: f"<span class='muted'>{escape(v)}</span>",
                ),
                Col(
                    "present",
                    "In data/raw",
                    fmt=lambda v, r: (
                        theme.pill("approved", "Present")
                        if v
                        else theme.pill("at risk", "Received, incomplete: simulated")
                        if r["received"]
                        else theme.pill("rejected", "Missing: simulated")
                    ),
                ),
            ],
        ),
        unsafe_allow_html=True,
    )
    if st.button("Rebuild analysis tables", icon=":material/refresh:"):
        from irerero.data.validate import SchemaError
        from irerero.pipeline.build import build

        try:
            with st.spinner("Rebuilding..."):
                build(eng=eng)
                from sqlalchemy.orm import Session

                with Session(eng) as s:
                    audit.write(s, user, "data.rebuild", "data", "all")
                    s.commit()
            data.clear()
            st.success("Rebuilt. Plans, check-ins, course progress and the audit log are kept.")
        except SchemaError as error:
            st.error(f"A data file does not match its schema: {error}")
