import numpy as np
import casadi as ca
from matplotlib import pyplot as plt
from trajopt_formulation import NLP1
from trajopt_formulation import NLP2

class TrajOptSolve():
    def __init__(self):
        super().__init__()
        self.formulation = NLP1(knot_points_per_phase=40, steps=2, total_duration=1, model='biped')
        p_opts = {"expand":True}
        s_opts = {"max_iter": 3000}
        self.formulation.opti.solver("ipopt",p_opts,s_opts)

    def solve(self):
        sol = self.formulation.opti.solve_limited()
        self.sol_lq1  = [] 
        self.sol_dlq1 = []
        
        self.sol_lq2  = [] 
        self.sol_dlq2 = []
        
        self.sol_rq1  = [] 
        self.sol_drq1 = []

        self.sol_rq2  = [] 
        self.sol_drq2 = []

        self.sol_tq  = [] 
        self.sol_dtq = []

        self.sol_lpx  = [] 
        self.sol_rpx  = []

        self.sol_lpy  = [] 
        self.sol_rpy  = []

        self.sol_lf  = [] 
        self.sol_rf  = []

        self.sol_u1 = []
        self.sol_u2 = []
        self.sol_u3 = []
        self.sol_u4 = []


        for keys in self.formulation.lq:
            self.sol_lq1.append(sol.value(self.formulation.lq[keys][0]))
            self.sol_rq1.append(sol.value(self.formulation.rq[keys][0]))

            self.sol_lq2.append(sol.value(self.formulation.lq[keys][1]))
            self.sol_rq2.append(sol.value(self.formulation.rq[keys][1]))

            self.sol_tq.append(sol.value(self.formulation.tq[keys][0]))

            self.sol_dlq1.append(sol.value(self.formulation.lqdot[keys][0]))
            self.sol_drq1.append(sol.value(self.formulation.rqdot[keys][0]))

            self.sol_dlq2.append(sol.value(self.formulation.lqdot[keys][1]))
            self.sol_drq2.append(sol.value(self.formulation.rqdot[keys][1]))

            self.sol_dtq.append(sol.value(self.formulation.tqdot[keys][0]))

            self.sol_lf.append(np.linalg.norm(sol.value(self.formulation.lforce[keys])))
            self.sol_rf.append(np.linalg.norm(sol.value(self.formulation.rforce[keys])))

            self.sol_lpx.append(sol.value(self.formulation.lpos[keys][0]))
            self.sol_rpx.append(sol.value(self.formulation.rpos[keys][0]))
       
            self.sol_lpy.append(sol.value(self.formulation.lpos[keys][1]))
            self.sol_rpy.append(sol.value(self.formulation.rpos[keys][1]))

            self.sol_u1.append(sol.value(self.formulation.u[keys][0]))
            self.sol_u2.append(sol.value(self.formulation.u[keys][1]))
            self.sol_u3.append(sol.value(self.formulation.u[keys][2]))
            self.sol_u4.append(sol.value(self.formulation.u[keys][3]))

        self.time = np.linspace(0.0, self.formulation.total_duration, len(self.sol_lq1))
        
    def plot(self):

        plt.subplot(521)
        plt.plot(self.time, self.sol_lq1, label='lq1')
        plt.plot(self.time, self.sol_lq2, label='lq2')
        plt.plot(self.time, self.sol_rq1, label='rq1')
        plt.plot(self.time, self.sol_rq2, label='rq2')
        plt.plot(self.time, self.sol_tq , label='tq ')
        plt.legend()

        plt.subplot(522)
        plt.plot(self.time, self.sol_dlq1, label='dlq1')
        plt.plot(self.time, self.sol_dlq2, label='dlq2')
        plt.plot(self.time, self.sol_drq1, label='drq1')
        plt.plot(self.time, self.sol_drq2, label='drq2')
        plt.plot(self.time, self.sol_dtq , label='dtq ')
        plt.legend()

        plt.subplot(523)
        plt.plot(self.time, self.sol_u1, label='u1')
        plt.plot(self.time, self.sol_u2, label='u2')
        plt.plot(self.time, self.sol_u3, label='u3')
        plt.plot(self.time, self.sol_u4, label='u4')
        plt.legend()

        plt.subplot(524)
        plt.plot(self.time, self.sol_lf, label='lf')
        plt.plot(self.time, self.sol_rf, label='rf')
        plt.legend()

        plt.subplot(525)
        plt.plot(self.time, self.sol_lpx, label='lpx')
        plt.plot(self.time, self.sol_lpy, label='lpy')
        plt.plot(self.time, self.sol_rpx, label='rpx')
        plt.plot(self.time, self.sol_rpy, label='rpy')
        plt.legend()

        plt.show()
        # print(self.sol_q)
        # print(self.sol_qdot)

######################################
# Remodel the dynamics according to h#
######################################

problem = TrajOptSolve()
problem.solve()
problem.plot()
