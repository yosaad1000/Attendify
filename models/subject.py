class Subject:
    """
    Represents an academic subject/course
    """
    def __init__(self, subject_id, name, department_id, faculty_ids=None, 
                 credits=None, is_elective=False):
        self.subject_id = subject_id      # Subject ID (used as document ID)
        self.name = name                  # Subject name
        self.department_id = department_id # Department the subject belongs to
        self.faculty_ids = faculty_ids or [] # List of faculty IDs teaching this subject
        self.credits = credits            # Number of credits
        self.is_elective = is_elective    # Whether the subject is an elective
    
    @staticmethod
    def from_dict(source):
        """Creates a Subject instance from a dictionary"""
        subject = Subject(
            subject_id=source.get('subject_id'),
            name=source.get('name'),
            department_id=source.get('department_id'),
            faculty_ids=source.get('faculty_ids', []),
            credits=source.get('credits'),
            is_elective=source.get('is_elective', False)
        )
        return subject
    
    def to_dict(self):
        """Returns the subject as a dictionary"""
        return {
            'subject_id': self.subject_id,
            'name': self.name,
            'department_id': self.department_id,
            'faculty_ids': self.faculty_ids,
            'credits': self.credits,
            'is_elective': self.is_elective
        }