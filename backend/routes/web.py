from __future__ import annotations

from flask import Blueprint, render_template

from .wrapper import login_required

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def home():
    """
    Home page
    """
    # If user in session, render home page
    # else, redirect to login page
    pass

@web_bp.route("/register")
def register():
    """
    Register page
    """
    pass

@web_bp.route("/login")
def login():
    """
    Login page
    """
    pass

@web_bp.route("/account")
@login_required
def account():
    """
    Account page
    """
    pass
