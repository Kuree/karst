from karst.values import *
from typing import List


class If(Statement):
    def __init__(self, parent):
        super().__init__(parent)
        # an if must have predicate, expression, and else expression
        # else expression can be empty
        self.predicate: Expression = None
        self.expressions: List[Expression] = []
        self.else_expressions: List[Expression] = []

    def __call__(self, predicate: Union[Expression, bool], *args: Expression):
        if isinstance(predicate, bool):
            self.predicate = Const(predicate)
        else:
            self.predicate = predicate
        self.expressions = list(args)
        # remove the expressions from parent context
        num_statements = len(self.expressions)
        for i in range(num_statements):
            # the last one is the if statement
            assert self.parent.context[-2].eq(self.expressions[-i])
            self.parent.context.pop(-2)
        return self

    def else_(self, *args: Expression):
        self.else_expressions = list(args)
        # remove the statements from the global context since we put it in the
        # local else_expressions
        num_statements = len(args)
        for i in range(num_statements):
            assert self.parent.context[-1] == args[-i]
            self.parent.context.pop(-1)
        return self

    def eval(self):
        if self.predicate.eval():
            for exp in self.expressions:
                exp.eval()
        else:
            for exp in self.else_expressions:
                exp.eval()

    def eq(self, other: "Statement"):
        if not isinstance(other, If):
            return False
        if not self.predicate.eq(other.predicate):
            return False
        else:
            if len(self.expressions) != len(other.expressions) or \
                    len(self.else_expressions) != len(other.else_expressions):
                return False
            for idx, exp in enumerate(self.expressions):
                if not exp.eq(other.expressions[idx]):
                    return False
            for idx, exp in enumerate(self.else_expressions):
                if not exp.eq(other.else_expressions[idx]):
                    return False
        return True

    Else = else_


class ReturnStatement(Statement):
    def __init__(self, values: Union[List[Value], Value], parent):
        super().__init__(parent)
        if isinstance(values, Variable):
            values = [values]
        self.values = values

        self.parent = parent

    def eval(self):
        return [v.eval() for v in self.values]

    def eq(self, other: "Statement"):
        if not isinstance(other, ReturnStatement):
            return False
        # need to compare if they are returning the same thing
        return len(self.values) == len(
            other.values) and set(self.values) == set(other.values)
