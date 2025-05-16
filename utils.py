LT = 'LESS_THAN'
GT = 'GREATER_THAN'
EQ = 'EQUAL'
# In most cases when comparing package versions, usual >, < operators will work (evaluates whichever operand has a greater character occur first as larger)
# However, there are common edge cases for version values that need to be covered first:
# 1) Format X.X.X; Consider 34.5.9; will be evaluated as less than 9.9.9
# .. More edge cases to be discovered!!!!!!!! waaaaaaaaaaaaaaaah!!!!!!!
def version_comp(v1, v2):
    if '.' in v1 and '.' in v2:
        v1_substrs = v1.split('.')
        v2_substrs = v2.split('.')
        for i in range(0, min(len(v1_substrs), len(v2_substrs))):
            if not v1_substrs[i].isdigit() or not v2_substrs[i].isdigit():
                print(f"[WARNING] From version_comp(): defaulting to string comparison for versions '{v1}' and '{v2}' since not fully numerical. COMPARISON MAY BE WRONG.")
            if int(v1_substrs[i]) > int(v2_substrs[i]):
                return GT
            elif int(v2_substrs[i]) > int(v1_substrs[i]):
                return LT
        return EQ
    
    comparison = EQ if v1 == v2 else (LT if v1 < v2 else GT)
    return comparison