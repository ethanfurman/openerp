from openerp.osv.fields import SelectionEnum

class ResultType(SelectionEnum):
    _order_ = 'pass_fail grade percent'
    pass_fail = 'Pass/Fail'
    grade = 'A, B, C, D, F'
    percent = "0 - 100%"


class ResultGrade(SelectionEnum):
    _order_ = 'a b c d f'
    a = 'A'
    b = 'B'
    c = 'C'
    d = 'D'
    f = 'F'


class ResultPassFail(SelectionEnum):
    _order_ = 'passing failing'
    passing = 'pass', 'Pass'
    failing = 'fail', 'Fail'


class Gender(SelectionEnum):
    _order_ = 'female male'
    male = 'Male'
    female = 'Female'


class Marital(SelectionEnum):
    _order_ = 'single married widower divorced'
    single = 'Single'
    married = 'Married'
    widower = 'Widow(er)'
    divorced = 'Divorced'


class JobState(SelectionEnum):
    _order_ = 'open recruit'
    open = 'No Recruitment'
    recruit = 'Recruitment in Progress'


class EmploymentType(SelectionEnum):
    _order_ = 'standard temporary contract'
    standard = "Permanent"
    temporary = "Temporary"
    contract = "Contract"
    @property
    def list_view_abbr(self):
        return {'standard': False, 'temporary': 'T', 'contract': 'C'}[self]

if EmploymentType.standard.list_view_abbr is not False:
    print("Problem with EmploymentType enum")
