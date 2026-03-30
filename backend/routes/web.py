from __future__ import annotations

from flask import Blueprint, render_template

from .wrapper import login_required

web_bp = Blueprint("web", __name__)

@web_bp.get("/")
def home():
    """
    Home page
    """
    # If user in session, render home page
    # else, redirect to login page
    pass

@web_bp.get("/register")
def register():
    """
    Register page
    """
    pass

@web_bp.get("/login")
def login():
    """
    Login page
    """
    pass

@web_bp.get("/account")
@login_required
def account():
    """
    Account page
    """
    pass
