from django.contrib.auth import authenticate, get_user_model, login, logout

User = get_user_model()


class Auth:
    def register_user(self, request, first_name, last_name, email, password):
        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            login(request, user)

            return {
                "status": True,
                "message": "Registration successful.",
                "data": {
                    "user": self._get_user_data(user),
                },
                "http_status": 201,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Registration failed: {str(exc)}",
                "data": None,
                "http_status": 500,
            }

    def login_user(self, request, email, password):
        try:
            user = authenticate(request, username=email, password=password)

            if user is None:
                return {
                    "status": False,
                    "message": "Invalid email or password.",
                    "data": None,
                    "http_status": 401,
                }

            login(request, user)

            return {
                "status": True,
                "message": "Login successful.",
                "data": {
                    "user": self._get_user_data(user),
                },
                "http_status": 200,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Login failed: {str(exc)}",
                "data": None,
                "http_status": 500,
            }

    def logout_user(self, request):
        logout(request)
        return {
            "status": True,
            "message": "Logout successful.",
            "data": None,
            "http_status": 200,
        }

    def current_user(self, user):
        if not user.is_authenticated:
            return {
                "status": True,
                "message": "Anonymous user.",
                "data": {
                    "authenticated": False,
                    "user": None,
                },
                "http_status": 200,
            }

        return {
            "status": True,
            "message": "Authenticated user.",
            "data": {
                "authenticated": True,
                "user": self._get_user_data(user),
            },
            "http_status": 200,
        }

    # ***************
    # *   Private   *
    # ***************
    
    def _get_user_data(self, user):
        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }
