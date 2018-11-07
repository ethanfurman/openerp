from openerp.osv.fields import SelectionEnum

class Gender(SelectionEnum):
    male = 'Male'
    female = 'Female'

class Marital(SelectionEnum):
    single = 'Single'
    married = 'Married'
    widower = 'Widower'
    divorced = 'Divorced'

class JobState(SelectionEnum):
    open = 'No Recruitment'
    recruit = 'Recruitment in Progress'

class EmploymentType(SelectionEnum):
    standard = "Permanent"
    temporary = "Temporary"
    contract = "Contract"
    @property
    def list_view_abbr(self):
        return {'standard': False, 'temporary': 'T', 'contract': 'C'}[self]


if EmploymentType.standard.list_view_abbr is not False:
    print("Problem with EmploymentType enum")
