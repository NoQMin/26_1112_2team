"""업무 데이터 오류를 모든 화면에서 같은 방식으로 안내한다."""
import streamlit as st


def load_or_stop(loader):
    try:
        return loader()
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        st.stop()
