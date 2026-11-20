import sys, math; sys.path.insert(0, ".")
from core.pipe import *
A = lambda D: math.pi * D * D / 4
rows = []
def chk(name, got, exp, rtol):
    ok = abs(got - exp) <= rtol * abs(exp)
    rows.append(ok); print(f"{'PASS' if ok else 'FAIL'} {name}: got {got:.6g} spec {exp:.6g}")
r = from_flow(1e-5, .02, 10); chk("1 V", r.V, .03183, 1e-3); chk("1 Re", r.Re, 636.62, 1e-3); chk("1 f", r.f, .10053, 1e-3); chk("1 hf", r.hf, .002596, 2e-3)
r = head_loss(.05, .01, 5); chk("2 Re", r.Re, 500, 1e-9); chk("2 hf", r.hf, .008155, 1e-3); chk("2 dP", r.dP, 80.0, 2e-3)
r = head_loss(2, .05, 100, f=.025); chk("3 hf", r.hf, 10.194, 1e-3); chk("3 dP", r.dP, 100e3, 1e-3)
r = head_loss(.04, .025, 8); chk("4 f", r.f, .064, 1e-9); chk("4 hf", r.hf, .001670, 2e-3)
r = from_flow(.005, .05, 80, 4.5e-5); chk("5 V", r.V, 2.5465, 1e-4); chk("5 Re", r.Re, 127324, 1e-4); chk("5 f", r.f, .02134528, 1e-4); chk("5 hf", r.hf, 11.288, 2e-3); chk("5 dP", r.dP, 110.73e3, 2e-3)
r = head_loss(1.5, .08, 150, 1.5e-4); chk("6 f", r.f, .02451, 2e-3); chk("6 hf", r.hf, 5.271, 2e-3); chk("6 dP", r.dP, 51.71e3, 2e-3)
chk("7 f", friction_factor(48000, .0025), .02770, 2e-3); chk("7 L", length_for_head(3, 1.2, .04, 1e-4), 59.03, 3e-3)
V = velocity_for_head(2, .06, 50, 6e-5); chk("8 V", V, 1.4471, 2e-3); chk("8 Q", V*A(.06), .004092, 2e-3)
a = from_flow(.004, .08, 60, 4.5e-5); b = from_flow(.004, .05, 40, 4.5e-5)
chk("9 hf1", a.hf, .5302, 2e-3); chk("9 hf2", b.hf, 3.6877, 2e-3); chk("9 dP", a.dP + b.dP, 41.38e3, 2e-3)
V = velocity_for_head(8, .075, 200, 1.5e-4); chk("10 V", V, 1.5374, 2e-3); chk("10 Q", V*A(.075), .006792, 2e-3)
print(f"\n{sum(rows)}/{len(rows)} passed")
