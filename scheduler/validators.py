from django.core.exceptions import ValidationError

class FourDigitPasswordValidator:
    def validate(self, password, user=None):
        if not password.isdigit() or len(password) != 4:
            raise ValidationError(
                "Password must be exactly 4 digits (e.g., 1000, 6005)."
            )

    def get_help_text(self):
        return "Your password must be exactly 4 numeric digits."
