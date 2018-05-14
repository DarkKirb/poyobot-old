%function pi()
%return 3.1415926535897932384626433832795028
%endfunction
%function e()
%return 2.718281828459045235360287471352662497757247093699959574966
%endfunction
%function i()
%return pow(-1,0.5)
%endfunction
%function copysign(x,y)
%if y < 0
%return -abs(x)
%else
%return abs(x)
%end
%endfunction
%function factorial(x)
o=1
%while x > 0
o = o * x
x = x - 1
%end
%return o
%endfunction
%function gcd(a, b)
%while b != 0
t = b
b = mod(a,b)
a = t
%end
%return a
%endfunction
%function square(val)
%return pow(val, 2)
%endfunction
%function exp(val)
%return pow(e(), val)
%endfunction
%function sqrt(val)
%return pow(val, 0.5)
%endfunction
%function ln(val)
%return log(val, e())
%endfunction
%function lg(val)
%return log(val, 10)
%endfunction
%function log2(val)
%return log(val, 2)
%endfunction
%function acos(x)
pihalf = pi()/2
oneminusxsquare = 1 - square(x)
denominator = sqrt(oneminusxsquare)
ratio = x / denominator
atan = atan(ratio)
%return pihalf - atan
%endfunction
%function asin(x)
%return acos(-x) - pi()/2
%endfunction
%function hypot(x, y)
%return sqrt(square(x) + square(y))
%endfunction
%function sin(x)
%return cos(pi()/2 - x)
%endfunction
%function tan(x)
%return sin(x)/cos(x)
%endfunction
%function cosh(x)
%return (exp(x)+exp(-x))/2
%endfunction
%function sinh(x)
%return (exp(x)-exp(-x))/2
%endfunction
%function tanh(x)
%return sinh(x)/cosh(x)
%endfunction
%function asinh(x)
%return ln(sqrt(square(x)+1)+x)
%endfunction
%function acosh(x)
%return ln(x+sqrt(x-1)*sqrt(x+1))
%endfunction
%function atanh(x)
%return ln(x+1)/2 - ln(1-x)/2
%endfunction
%function init()
retval = {}
%return retval
%endfunction
