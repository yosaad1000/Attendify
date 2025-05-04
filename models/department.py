class Department:
    """
    Represents an academic department
    """
    def __init__(self, dept_id, name, hod=None):
        self.dept_id = dept_id  # Department ID (used as document ID)
        self.name = name        # Department name
        self.hod = hod          # Head of Department (faculty_id)
    
    @staticmethod
    def from_dict(source):
        """Creates a Department instance from a dictionary"""
        department = Department(
            dept_id=source.get('dept_id'),
            name=source.get('name'),
            hod=source.get('hod')
        )
        return department
    
    def to_dict(self):
        """Returns the department as a dictionary"""
        return {
            'dept_id': self.dept_id,
            'name': self.name,
            'hod': self.hod
        }