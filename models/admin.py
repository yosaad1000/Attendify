class Admin:
    """
    Represents an admin user
    """
    def __init__(self, admin_id, name, email, role="admin"):
        self.admin_id = admin_id  # Admin ID (used as document ID)
        self.name = name          # Admin name
        self.email = email        # Admin email
        self.role = role          # Role: admin, super_admin
    
    @staticmethod
    def from_dict(source):
        """Creates an Admin instance from a dictionary"""
        admin = Admin(
            admin_id=source.get('admin_id'),
            name=source.get('name'),
            email=source.get('email'),
            role=source.get('role', 'admin')
        )
        return admin
    
    def to_dict(self):
        """Returns the admin as a dictionary"""
        return {
            'admin_id': self.admin_id,
            'name': self.name,
            'email': self.email,
            'role': self.role
        }