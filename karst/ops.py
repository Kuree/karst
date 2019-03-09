from karst.values import *


class Operator:
    def __init__(self, parent):
        self.parent = parent

    @abc.abstractmethod
    def eval(self):
        pass


class If(Operator):
    def __init__(self, parent):
        super().__init__(parent)
        # an if must have predicate, expression, and else expression
        # else expression can be empty
        self.predicate: Expression = None
        self.expression: Expression = None
        self.else_expression: Expression = None

        self.parent.context.append(self)

    def __call__(self, predicate: Expression, expression: Expression):
        self.predicate = predicate
        self.expression = expression

    def Else(self, expression: Expression):
        self.else_expression = expression

    def eval(self):
        if self.predicate.eval():
            self.expression.eval()
        else:
            if self.else_expression is not None:
                self.else_expression.eval()


