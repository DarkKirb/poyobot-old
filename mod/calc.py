"""This module implements a small programming language and virtual machine"""
from utils import Cog, command
import discord
from discord.ext import commands
import math
import cmath


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/calc.py"
__version__ = "1.0"
dependencies = []


with open("data/commonfunc.cl") as f:
    template = f.read()


async def ceil(stack):
    a = stack.pop()
    if isinstance(a, MathOp):
        stack.append(CeilOp(a))
    else:
        stack.append(math.ceil(a))


async def mod(stack):
    b, a = stack.pop(), stack.pop()
    if isinstance(a, MathOp) or isinstance(b, MathOp):
        stack.append(ModOp(makeop(a), makeop(b)))
    else:
        stack.append(a % b)


async def log(stack):
    b, a = stack.pop(), stack.pop()
    if isinstance(a, complex) or isinstance(b, complex):
        stack.append(cmath.log(a) / cmath.log(b))
    elif isinstance(a, MathOp) or isinstance(b, MathOp):
        stack.append(LogOp(makeop(a), makeop(b)))


async def npow(stack):
    b, a = stack.pop(), stack.pop()
    if isinstance(a, MathOp) or isinstance(b, MathOp):
        stack.append(PowOp(makeop(a), makeop(b)))
    else:
        stack.append(a ** b)


async def nabs(stack):
    a = stack.pop()
    if isinstance(a, MathOp):
        stack.append(AbsOp(a))
    else:
        stack.append(abs(a))


async def cos(stack):
    a = stack.pop()
    if isinstance(a, complex):
        stack.append(cmath.cos(a))
    else:
        stack.append(cmath.cos(a))


async def atan(stack):
    a = stack.pop()
    if isinstance(a, complex):
        stack.append(cmath.atan(a))
    else:
        stack.append(math.atan(a))


async def napply(stack):
    x, fun = stack.pop(), stack.pop()
    stack.append(fun(x))


async def derive(stack):
    stack.append(stack.pop().derive())


async def xop(stack):
    stack.append(VarOp())


output = []
variables = []
ofunctions = {"CEIL": ceil, "MOD": mod, "LOG": log, "POW": npow, "ABS": nabs,
              "COS": cos, "ATAN": atan, "APPLY": napply, "DERIVE": derive,
              "X": xop}
functions = ofunctions.copy()

functionname = ""

t = ""
look = ""


async def getChar():
    global t, look
    look = t[:1]
    t = t[1:]


async def error(msg):
    output.append(msg)


async def abort(msg):
    await error(msg)
    raise ValueError(msg)


async def expected(msg):
    await abort(f"{msg} expected")


async def match(c):
    if look == c:
        await getChar()
        await skip_white()
    else:
        await expected(c)


async def is_alpha(c):
    return c.isalpha()


async def is_digit(c):
    return c.isdigit() or c == "."


async def is_alnum(c):
    return c.isalpha() or c.isdigit()


async def is_white(c):
    return c in " \t"


async def skip_white():
    while look and await is_white(look):
        await getChar()


async def get_name():
    token = ""
    if not await is_alpha(look):
        await expected("name")
    while await is_alnum(look):
        token += look.upper()
        await getChar()
    await skip_white()
    return token


async def get_num():
    token = ""
    if not await is_digit(look):
        await expected("number")
    while await is_digit(look):
        token += look
        await getChar()
    await skip_white()
    if "." not in token:
        return int(token)
    else:
        return float(token)


async def emitln(thing):
    output.append(thing)


async def init():
    await getChar()
    await skip_white()
    while look != "":
        await block()
        if not look:
            return
        elif look != "\n":
            await expected("newline")
        else:
            await match("\n")


async def ident(n=None):
    if n is None:
        n = await get_name()

    if look != "(":
        await emitln(PushVar(variables.index(n)))
    else:
        argcount = 0
        await match("(")
        while look != ")":
            argcount += 1
            await expression()
            if look != ")":
                await match(",")
        await match(")")
        await emitln(CallIns(n))


async def factor():
    if look == "(":
        await match("(")
        await expression()
        await match(")")
    elif await is_alpha(look):
        await ident()
    else:
        await emitln(PushIns(await get_num()))


async def mul():
    await match("*")
    await factor()
    await emitln(MulIns())


async def div():
    await match("/")
    await factor()
    await emitln(DivIns())


async def term():
    await factor()
    while look and look in "*/":
        if look == "*":
            await mul()
        else:
            await div()


async def add():
    await match("+")
    await term()
    await emitln(AddIns())


async def sub():
    await match("-")
    await term()
    await emitln(SubIns())


async def expression():
    if look and look in "+-":
        await emitln(PushIns(0))
    else:
        await term()
    while look and look in "+-":
        if look == "+":
            await add()
        else:
            await sub()


async def assignment():
    global look
    if not await is_alpha(look):
        await expression()
        return await emitln(PopZero())
    n = await get_name()
    if look != "=":
        # undo that
        global t
        t = n[1:] + look + t
        look = n[0]
        await expression()
        return await emitln(PopZero())
    await match("=")
    await expression()
    if n not in variables:
        variables.append(n)
    await emitln(PopVar(variables.index(n)))


async def function():
    global functionname
    functionname = await get_name()
    functions[functionname] = len(output)
    await match("(")
    while look != ")":
        await emitln(PopVar(len(variables)))
        variables.append(await get_name())
        if look != ")":
            await match(",")
    await match(")")


async def return_statement():
    await expression()
    await emitln(ReturnIns())


async def endfunction():
    global functionname
    global variables
    functionname = ""
    variables = []


async def comparison():
    await expression()
    comptype = 0
    if look == "=":
        await match("=")
        await match("=")
    elif look == "<":
        await match("<")
        comptype -= 2
        if look == "=":
            await match("=")
            comptype += 1
    elif look == ">":
        await match(">")
        comptype += 2
        if look == "=":
            await match("=")
            comptype -= 1
    elif look == "!":
        await match("!")
        await match("=")
        comptype += 3
    else:
        await expected("compop")

    await expression()
    if comptype == -2:
        x = JumpGeIns(None)
    elif comptype == -1:
        x = JumpGtIns(None)
    elif comptype == 0:
        x = JumpNeIns(None)
    elif comptype == 1:
        x = JumpLtIns(None)
    elif comptype == 2:
        x = JumpLeIns(None)
    elif comptype == 3:
        x = JumpEqIns(None)
    await emitln(x)
    return x


currifskips = []
currelseskips = []


class EndOfBlockError(BaseException):
    def __init__(self, blocktype):
        self.blocktype = blocktype


async def ifblock():
    currifskips.append(await comparison())
    t = None
    try:
        await init()
    except EndOfBlockError as e:
        t = e
        if e.blocktype:
            x = JumpIns(None)
            await emitln(x)
            currelseskips.append(x)
    x = currifskips.pop()
    x.dest = len(output)
    if t.blocktype:
        await elseblock(True)


async def elseblock(cont=False):
    if not cont:
        raise EndOfBlockError(True)
    try:
        await init()
    except EndOfBlockError:
        pass
    x = currelseskips.pop()
    x.dest = len(output)


async def whileblock():
    startlbl = JumpIns(len(output))
    x = await comparison()
    try:
        await init()
    except EndOfBlockError:
        pass
    await emitln(startlbl)
    x.dest = len(output)


async def block():
    if look != "%" and functionname == "":
        await expected("Function")
    if look != "%":
        return await assignment()
    await match("%")
    blockname = await get_name()
    if blockname == "FUNCTION":
        await function()
    elif blockname == "RETURN":
        await return_statement()
    elif blockname == "ENDFUNCTION":
        await endfunction()
    elif blockname == "IF":
        await ifblock()
    elif blockname == "ELSE":
        await elseblock()
    elif blockname == "END":
        raise EndOfBlockError(False)
    elif blockname == "WHILE":
        await whileblock()
    else:
        await expected("Construct")


frames = []
current_vars = {}
callstack = []
pc = 0


class CallIns(object):
    def __init__(self, val):
        self.val = val

    async def __call__(self, stack):
        val = functions[self.val]
        if isinstance(val, int):
            global current_vars
            frames.append(current_vars)
            current_vars = {}
            global pc
            callstack.append(pc)
            pc = val - 1
        else:
            await val(stack)

    def __repr__(self):
        return "call {}".format(self.val)


class ReturnIns(object):
    def __init__(self):
        pass

    async def __call__(self, stack):
        global current_vars
        global pc
        current_vars = frames.pop()
        pc = callstack.pop()

    def __repr__(self):
        return "return"


class PushIns(object):
    def __init__(self, val):
        self.val = val

    async def __call__(self, stack):
        stack.append(self.val)

    def __repr__(self):
        return "push {}".format(self.val)


class PushVar(object):
    def __init__(self, val):
        self.val = val

    async def __call__(self, stack):
        stack.append(current_vars[self.val])

    def __repr__(self):
        return "pushv {}".format(self.val)


class PopZero(object):
    def __init__(self):
        pass

    async def __call__(self, stack):
        stack.pop()

    def __repr__(self):
        return "popz"


class PopVar(object):
    def __init__(self, val):
        self.val = val

    async def __call__(self, stack):
        current_vars[self.val] = stack.pop()

    def __repr__(self):
        return "popv {}".format(self.val)


class AddIns(object):
    def __init__(self):
        pass

    async def __call__(self, stack):
        a, b = stack.pop(), stack.pop()
        stack.append(a+b)

    def __repr__(self):
        return "add"


class SubIns(object):
    def __init__(self):
        pass

    async def __call__(self, stack):
        b, a = stack.pop(), stack.pop()
        stack.append(a-b)

    def __repr__(self):
        return "sub"


class MulIns(object):
    def __init__(self):
        pass

    async def __call__(self, stack):
        a, b = stack.pop(), stack.pop()
        stack.append(a*b)

    def __repr__(self):
        return "mul"


class DivIns(object):
    def __init__(self):
        pass

    async def __call__(self, stack):
        b, a = stack.pop(), stack.pop()
        stack.append(a/b)

    def __repr__(self):
        return "div"


class JumpIns(object):
    def __init__(self, dest):
        self.dest = dest
        pass

    async def __call__(self, stack):
        global pc
        pc = self.dest-1

    def __repr__(self):
        return "jmp {}".format(self.dest)


class JumpEqIns(object):
    def __init__(self, dest):
        self.dest = dest

    async def __call__(self, stack):
        global pc
        b, a = stack.pop(), stack.pop()
        if a == b:
            pc = self.dest - 1

    def __repr__(self):
        return "jmpeq {}".format(self.dest)


class JumpLtIns(object):
    def __init__(self, dest):
        self.dest = dest

    async def __call__(self, stack):
        global pc
        b, a = stack.pop(), stack.pop()
        if a < b:
            pc = self.dest - 1

    def __repr__(self):
        return "jmplt {}".format(self.dest)


class JumpGtIns(object):
    def __init__(self, dest):
        self.dest = dest

    async def __call__(self, stack):
        global pc
        b, a = stack.pop(), stack.pop()
        if a > b:
            pc = self.dest - 1

    def __repr__(self):
        return "jmpgt {}".format(self.dest)


class JumpLeIns(object):
    def __init__(self, dest):
        self.dest = dest

    async def __call__(self, stack):
        global pc
        b, a = stack.pop(), stack.pop()
        if a <= b:
            pc = self.dest - 1

    def __repr__(self):
        return "jmple {}".format(self.dest)


class JumpGeIns(object):
    def __init__(self, dest):
        self.dest = dest

    async def __call__(self, stack):
        global pc
        b, a = stack.pop(), stack.pop()
        if a >= b:
            pc = self.dest - 1

    def __repr__(self):
        return "jmpge {}".format(self.dest)


class JumpNeIns(object):
    def __init__(self, dest):
        self.dest = dest

    async def __call__(self, stack):
        global pc
        b, a = stack.pop(), stack.pop()
        if a != b:
            pc = self.dest - 1

    def __repr__(self):
        return "jmpne {}".format(self.dest)


def makeop(x):
    if isinstance(x, MathOp):
        return x
    return ConstOp(x)


class MathOp:
    def __repr__(self):
        return "(???)"

    def __call__(self, x):
        return 0

    def __add__(self, other):
        return AddOp(self, makeop(other))

    def __sub__(self, other):
        return SubOp(self, makeop(other))

    def __mul__(self, other):
        return MulOp(self, makeop(other))

    def __truediv__(self, other):
        return DivOp(self, makeop(other))

    def __pow__(self, other):
        return PowOp(self, makeop(other))

    def __neg__(self):
        return NegOp(self)

    def __pos__(self):
        return self

    def __abs__(self):
        return AbsOp(self)

    def derive():
        return MathOp()

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True


class ConstOp(MathOp):
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return repr(self.val)

    def __call__(self, x):
        return self.val

    def __add__(self, other):
        if isinstance(other, (ConstOp, int, float)):
            return ConstOp(self.val + makeop(other).val)
        if self.val == 0:
            return other
        return super().__add__(other)

    def __sub__(self, other):
        if isinstance(other, (ConstOp, int, float)):
            return ConstOp(self.val - makeop(other).val)
        if self.val == 0:
            return -other
        return super().__sub__(other)

    def __mul__(self, other):
        if isinstance(other, (ConstOp, int, float)):
            return ConstOp(self.val * makeop(other).val)
        if self.val == 0:
            return self
        if self.val == 1:
            return other
        return super().__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, (ConstOp, int, float)):
            return ConstOp(self.val / makeop(other).val)
        if self.val == 0:
            return self
        return super().__truediv__(other)

    def __pow__(self, other):
        if isinstance(other, (ConstOp, int, float)):
            return ConstOp(self.val ** makeop(other).val)
        if self.val == 0 or self.val == 1:
            return self
        return super().__pow__(other)

    def __radd__(self, lhs):
        return self + lhs

    def __rsub__(self, lhs):
        return -self + lhs

    def __rmul__(self, lhs):
        return self * lhs

    def __rdiv__(self, lhs):
        if self.val == 0:
            raise ZeroDivisionError()
        if self.val == 1:
            return lhs
        return DivOp(lhs, self)

    def __rpow__(self, lhs):
        if self.val == 0:
            return ConstOp(1)
        if self.val == 1:
            return lhs
        return PowOp(lhs, self)

    def __neg__(self):
        return ConstOp(-self.val)

    def __abs__(self):
        return ConstOp(abs(self.val))

    def derive(self):
        return ConstOp(0)

    def function_of_x(self):
        return False

    def __eq__(self, other):
        if not isinstance(other, ConstOp):
            return False
        return self.val == other.val

    def __ne__(self, other):
        return not (self == other)


class EOp(ConstOp):
    def __init__(self):
        super().__init__(math.e)

    def __repr__(self):
        return "e"


class VarOp(MathOp):
    def __repr__(self):
        return "x"

    def __call__(self, x):
        return x

    def derive(self):
        return ConstOp(1)

    def function_of_x(self):
        return True

    def __eq__(self, other):
        return isinstance(other, VarOp)

    def __ne__(self, other):
        return not (self == other)


class AddOp(MathOp):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "(" + repr(self.lhs)+") + (" + repr(self.rhs) + ")"

    def __call__(self, x):
        return self.lhs(x) + self.rhs(x)

    def derive(self):
        if not self.lhs.function_of_x():
            return self.rhs.derive()
        elif not self.rhs.function_of_x():
            return self.lhs.derive()
        return self.lhs.derive() + self.rhs.derive()

    def function_of_x(self):
        return self.lhs.function_of_x() or self.rhs.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, AddOp):
            return False
        return (self.lhs == other.lhs and self.rhs == other.rhs) or \
            (self.rhs == other.lhs and self.lhs == other.rhs)

    def __ne__(self, other):
        return not (self == other)


class SubOp(MathOp):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "(" + repr(self.lhs)+") - ("+repr(self.rhs)+")"

    def __call__(self, x):
        return self.lhs(x) - self.rhs(x)

    def derive(self):
        if not self.lhs.function_of_x():
            return -self.rhs.derive()
        elif not self.rhs.function_of_x():
            return self.lhs.derive()
        return self.lhs.derive() - self.rhs.derive()

    def function_of_x(self):
        return self.lhs.function_of_x() or self.rhs.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, SubOp):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __ne__(self, other):
        return not (self == other)


class MulOp(MathOp):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "("+repr(self.lhs)+") ("+repr(self.rhs)+")"

    def __call__(self, x):
        return self.lhs(x) * self.rhs(x)

    def derive(self):
        if not self.lhs.function_of_x():
            return self.lhs * self.rhs.derive()
        if not self.rhs.function_of_x():
            return self.rhs + self.lhs.derive()
        return self.lhs.derive() * self.rhs + self.lhs * self.rhs.derive()

    def function_of_x(self):
        return self.lhs.function_of_x() or self.rhs.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, MulOp):
            return False
        return (self.lhs == other.lhs and self.rhs == other.rhs) \
            or (self.rhs == other.lhs and self.lhs == other.rhs)

    def __ne__(self, other):
        return not (self == other)


class DivOp(MathOp):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "("+repr(self.lhs)+") / ("+repr(self.rhs)+")"

    def __call__(self, x):
        return self.lhs(x) / self.rhs(x)

    def derive(self):
        if not self.lhs.function_of_x():
            return (-self.lhs * self.rhs.derive()) / (self.rhs ** 2)
        if not self.rhs.function_of_x():
            return self.lhs.derive() / self.rhs
        return (self.lhs.derive() * self.rhs - self.lhs *
                self.rhs.derive())/(self.rhs ** 2)

    def function_of_x(self):
        return self.lhs.function_of_x() or self.rhs.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, DivOp):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __ne__(self, other):
        return not (self == other)


class PowOp(MathOp):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "("+repr(self.lhs)+") ^ ("+repr(self.rhs)+")"

    def __call__(self, x):
        return self.lhs(x) ** self.rhs(x)

    def derive(self):
        if not self.lhs.function_of_x():
            if not isinstance(self.lhs, EOp) and \
                    not isinstance(self.rhs, VarOp):
                return self.lhs**self.rhs * LogOp(self.lhs) * self.rhs.derive()
            elif not isinstance(self.lhs, EOp) and isinstance(self.rhs, VarOp):
                return self.lhs**self.rhs * LogOp(self.lhs)
            elif isinstance(self.lhs, EOp) and not isinstance(self.rhs, VarOp):
                return self.lhs**self.rhs * self.rhs.derive()
            else:
                return self.lhs**self.rhs
        if not self.rhs.function_of_x():
            if not isinstance(self.lhs, VarOp):
                return self.rhs * self.lhs ** (self.rhs-1) * self.lhs.derive()
            else:
                return self.rhs * self.lhs ** (self.rhs-1)
        return self.lhs**(self.rhs-1) * (self.rhs * self.lhs.derive() +
                                         self.lhs * LogOp(self.lhs) *
                                         self.rhs.derive())

    def function_of_x(self):
        return self.lhs.function_of_x() or self.rhs.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, PowOp):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __ne__(self, other):
        return not (self == other)


class NegOp(MathOp):
    def __init__(self, term):
        self.term = term

    def __repr__(self):
        return "-("+repr(self.term)+")"

    def __call__(self, x):
        return -self.term(x)

    def derive(self):
        return -self.term.derive()

    def function_of_x(self):
        return self.term.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, NegOp):
            return False
        return self.term == other.term

    def __ne__(self, other):
        return not (self == other)


class AbsOp(MathOp):
    def __init__(self, term):
        self.term = term

    def __repr__(self):
        return "|" + repr(self.term) + "|"

    def __call__(self, x):
        return abs(self.term(x))

    def derive(self):
        return (self.term * self.term.derive()) / self

    def function_of_x(self):
        return self.term.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, AbsOp):
            return False
        return self.term == other.term

    def __ne__(self, other):
        return not (self == other)


class LogOp(MathOp):
    def __init__(self, term):
        self.term = term

    def __repr__(self):
        return "ln("+repr(self.term)+")"

    def __call__(self, x):
        return math.log(self.term(x))

    def derive(self):
        return self.term.derive() / self.term

    def function_of_x(self):
        return self.term.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, AbsOp):
            return False
        return self.term == other.term

    def __ne__(self, other):
        return not (self == other)


class SplitFunOp(MathOp):
    def __init__(self, *terms):
        self.terms = terms

    def __repr__(self):
        string = "{"
        for term, comparator, comparator_str in self.terms:
            string += f"({term}) for {comparator_str}; "
        string += "}"
        return string

    def __call__(self, x):
        for term, comparator, comparator_str in self.terms:
            if comparator(x):
                return term(x)

    def derive(self):
        terms = []
        for term, comparator, comparator_str in self.terms:
            terms.append((term.derive), comparator, comparator_str)
        return SplitFunOp(*terms)

    def function_of_x(self):
        return True

    def __eq__(self, other):
        if not isinstance(other, SplitFunOp):
            return False
        return self.terms == other.terms

    def __ne__(self, other):
        return not (self == other)


class InvOp(MathOp):
    def __repr__(self):
        return "UNDEFINED"

    def __call__(self, x):
        raise ArithmeticError("Tried to evaluate undefined expression.")

    def derive(self):
        return self

    def function_of_x(self):
        return True

    def __eq__(self, other):
        return isinstance(InvOp)

    def __ne__(self, other):
        return not (self == other)


class CeilOp(MathOp):
    def __init__(self, term):
        self.term = term

    def __repr__(self):
        return f"ceil({self.term})"

    def __call__(self, x):
        return math.ceil(self.term(x))

    def _cmpop(self, x):
        return math.ceil(x) == math.floor(x)

    def derive(self):
        return SplitFunOp(
            (ConstOp(0), lambda x: not self._cmpop(self.term(x)),
             f"f(x) ∉ ℤ"),
            (InvOp(), lambda x: self._cmpop(self.term(x)),
             f"f(x) ∈ ℤ")
        )

    def function_of_x(self, other):
        return self.term.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.term == other.term

    def __ne__(self, other):
        return not (self == other)


class FloorOp(CeilOp):
    def __repr__(self):
        return f"floor({self.term})"

    def __call__(self, x):
        return int(self.term(x))


class ModOp(MathOp):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return f"({self.lhs}) % ({self.rhs})"

    def __call__(self, x):
        return self.lhs(x) % self.rhs(x)

    def _cmpop(self, x):
        return math.ceil(x) == math.floor(x)

    def _cmp(self, x):
        return self._cmpop(self.lhs(x) / self.rhs(x))

    def _deriv(self):
        return self.lhs.derive() - self.rhs.derive() * \
            FloorOp(self.lhs / self.rhs)

    def derive(self):
        return SplitFunOp(
            (self._deriv(), lambda x: not self._cmp(x), f"u(x)/v(x) ∉ ℤ"),
            (InvOp(), lambda x: self._cmp(x), f"u(x)/v(x) ∈ ℤ")
        )

    def function_of_x(self, other):
        return self.term.function_of_x()

    def __eq__(self, other):
        if not isinstance(other, CeilOp):
            return False
        return self.term == other.term

    def __ne__(self, other):
        return not (self == other)


class Calc(Cog):
    watch_files = ["data/commonfuncs.cl"]

    async def compile_code(self, code):
        global functions
        functions = ofunctions.copy()
        output.clear()
        global t
        t = template.format(code)
        await init()

    @command()
    async def compile(self, ctx, *, code: str):
        """This compiles code into bytecode"""
        await self.compile_code(code)
        paginator = commands.Paginator()
        for x in output[functions["INIT"]:]:
            paginator.add_line(repr(x))
        for page in paginator.pages:
            await ctx.send(page)

    @command()
    async def eval(self, ctx, *, code: str):
        """This is a calculator command. It supports the following:

```
- correct order of operation
- addition, subtraction, multiplication, division
- complex numbers (5 + i())
- the constants pi() and e()
- the following functions:
    - ceil(number): rounds towards infinity
    - mod(divisor, divident): returns the remainder of an integer devision
    - log(num, base): returns ln(num)/ln(base)
    - pow(base, exponent): returns base^exponent
    - abs(number): absolute value
    - sin(x), cos(x), tan(x)
    - asin(x), acos(x), atan(x)
    - sinh(x), cosh(x), tanh(x)
    - asinh(x), acosh(x), atanh(x)
    - copysign(a, b) - returns a with the same sign as b
    - factorial(a)
    - gcd(a, b) - greatest common divisor
    - square(x) = pow(x, 2)
    - sqrt(x) = pow(x, 0.5)
    - ln(x) = log(x, e())
    - lg(x) = log(x, 10)
    - log2(x) = log(x, 2)
    - hypot(x, y) = abs(x + y * i())
```"""
        await self.compile_code(code)
        global stack, current_vars, frames, callstack, pc
        stack = []
        current_vars = {}
        frames = [{}]
        callstack = [len(output)]
        pc = functions["INIT"]
        icount = 0
        while pc < len(output):
            if icount > 1000000:
                e = discord.Embed(title="Error", color=0xFF0000)
                e.set_footer(text="Eval exceeded 1,000,000 instructions")
                await ctx.send(embed=e)
                return
            await output[pc](stack)
            pc += 1
            icount += 1
        await ctx.send(stack.pop())


def setup(bot):
    global cog
    cog = Calc(bot)
