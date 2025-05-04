class Faculty:
    """
    Represents a faculty member/teacher
    """
    def __init__(self, faculty_id, name, email, departments, subjects=None):
        self.faculty_id = faculty_id  # Faculty ID (used as document ID)
        self.name = name              # Faculty name
        self.email = email            # Faculty email
        self.departments = departments  # List of department IDs the faculty belongs to
        self.subjects = subjects or [] # List of subject IDs the faculty teaches
    
    @staticmethod
    def from_dict(source):
        """Creates a Faculty instance from a dictionary"""
        faculty = Faculty(
            faculty_id=source.get('faculty_id'),
            name=source.get('name'),
            email=source.get('email'),
            departments=source.get('departments'),
            subjects=source.get('subjects', [])
        )
        return faculty
    
    def to_dict(self):
        """Returns the faculty as a dictionary"""
        return {
            'faculty_id': self.faculty_id,
            'name': self.name,
            'email': self.email,
            'departments': self.departments,
            'subjects': self.subjects
        }