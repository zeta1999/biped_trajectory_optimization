import numpy as np
import casadi as ca
from matplotlib import pyplot as plt

# from five_link_model import Biped1
# from five_link_model import Biped2

from hopper_model import Hopper

from terrain import Terrain

# import helper_functions as hf 

##############################################################
#### we will review the time phases division and other stuff again
#### we will review the time phases division and other stuff again
##############################################################


##############################################################
#### Go back to the old method of calculating, no params, only knot points
#### Have a speacial node between 2 phases so that two consecutive phases are related
##############################################################


##############################################################
#### so far we were building trajectories afterwards
#### now we will construct a trajectory first then optimise it
#### Also you parametrize feet and force with a spline, and calculate values at knot points
##############################################################

class NonlinearProgram():
    def __init__(self, dt, steps, total_duration, model='hopper', terrain='flat'):
        super().__init__()
        self.dt             = dt
        self.num_phases     = steps
        self.total_duration = total_duration

        self.knot_points = int(total_duration/dt)

        self.phase_knot_points = int(total_duration/dt)
        
        # print(self.phase_knot_points)

        if model == 'hopper':
            self.model = Hopper()
            self.time_phases = []
        
        self.terrain = Terrain(name=terrain)

        self.opti   = ca.Opti()

        self.q     = []
        self.q_dot = []
        self.r     = []
        self.r_dot = [] 
        self.p     = []
        self.p_dot = [] 
        self.f     = [] 
        self.f_dot = [] 

        self.q_ddot = []
        self.r_ddot = []

        self.ceq = []
        self.ciq = []

        self.q_variables     = []
        self.q_dot_variables = []
        self.r_variables     = []
        self.r_dot_variables = []

        self.p_variables     = []
        self.p_dot_variables = []
        self.f_dot_variables = []
        self.f_variables     = []

        # self.kinematic_constraint = []
        # self.e_constraint         = []
        # self.f_constraint         = []
        # self.df_constraint        = []
        # self.dynamic_constraint   = []

        self.setPolynomial()
        # self.setSpline()
        
        self.setPolyCoefficients()
        # self.contructPhaseSpline()
        # self.setVariables()

        self.setConstraints()
        # self.setInitialGuess()

        self.time = np.linspace(0.0, self.total_duration, len(self.f))

        # self.plotCallback()
        # # self.setBounds()
        self.printInfo()

    def setPolynomial(self):
        delta_T = ca.MX.sym('delta_T',1)
        t = ca.MX.sym('t', 1)

        ############################################################
        p0  = ca.MX.sym( 'p0_1', 2)
        p1  = ca.MX.sym( 'p1_1', 2)
        dp0 = ca.MX.sym('dp0_1', 2)
        dp1 = ca.MX.sym('dp1_1', 2)

        a0 = p0
        a1 = dp0
        a2 = -(delta_T**(-2))*(3*(p0 - p1) + delta_T*(2*dp0 + dp1))
        a3 = (delta_T**(-3))*(2*(p0 - p1) + delta_T*(dp0 + dp1))

        p = a0 + a1*t + a2*(t**2) + a3*(t**3)
        dp = a1 + 2*a2*t + 3*a3*(t**2)

        self.p_polynomial = ca.Function('end_effector', [delta_T, t, p0, dp0, p1, dp1], [p, dp], 
                                        ['delta_T', 't', 'p0', 'dp0', 'p1', 'dp1'], ['p', 'dp'])

        ############################################################
        f0  = ca.MX.sym( 'f0_1', 2)
        f1  = ca.MX.sym( 'f1_1', 2)
        df0 = ca.MX.sym('df0_1', 2)
        df1 = ca.MX.sym('df1_1', 2)

        a0 = f0
        a1 = df0
        a2 = -(delta_T**(-2))*(3*(f0 - f1) + delta_T*(2*df0 + df1))
        a3 = (delta_T**(-3))*(2*(f0 - f1) + delta_T*(df0 + df1))

        f = a0 + a1*t + a2*(t**2) + a3*(t**3)
        df = a1 + 2*a2*t + 3*a3*(t**2)

        self.f_polynomial = ca.Function('force', [delta_T, t, f0, df0, f1, df1], [f, df], 
                                        ['delta_T', 't', 'f0', 'df0', 'f1', 'df1'], ['f', 'df'])

        ############################################################
        q0  = ca.MX.sym( 'q0_1', 1)
        q1  = ca.MX.sym( 'q1_1', 1)
        dq0 = ca.MX.sym('dq0_1', 1)
        dq1 = ca.MX.sym('dq1_1', 1)

        a0 = q0
        a1 = dq0
        a2 = -(delta_T**(-2))*(3*(q0 - q1) + delta_T*(2*dq0 + dq1))
        a3 = (delta_T**(-3))*(2*(q0 - q1) + delta_T*(dq0 + dq1))

        q   = a0 + a1*t + a2*(t**2) + a3*(t**3)
        dq  = a1 + 2*a2*t + 3*a3*(t**2)
        ddq = 2*a2 + 6*a3*t

        # q   = a0*t + a1*(t**2) + a2*(t**3) + a3*(t**4)
        # dq  = a0 + 2*a1*t + 3*a2*(t**2) + 4*a3*(t**3)
        # ddq = 2*a1 + 6*a2*t + 12*a3*(t**2)

        self.q_polynomial = ca.Function('joint_angles', [delta_T, t, q0, dq0, q1, dq1], [q, dq, ddq], 
                                        ['delta_T', 't', 'q0', 'dq0', 'q1', 'dq1'], ['q', 'dq', 'ddq'])

        ############################################################
        r0  = ca.MX.sym( 'r0_1', 2)
        r1  = ca.MX.sym( 'r1_1', 2)
        dr0 = ca.MX.sym('dr0_1', 2)
        dr1 = ca.MX.sym('dr1_1', 2)

        a0 = r0
        a1 = dr0
        a2 = -(delta_T**(-2))*(3*(r0 - r1) + delta_T*(2*dr0 + dr1))
        a3 = (delta_T**(-3))*(2*(r0 - r1) + delta_T*(dr0 + dr1))

        r   = a0 + a1*t + a2*(t**2) + a3*(t**3)
        dr  = a1 + 2*a2*t + 3*a3*(t**2)
        ddr = 2*a2 + 6*a3*t

        # r   = a0*t + a1*(t**2) + a2*(t**3) + a3*(t**4)
        # dr  = a0 + 2*a1*t + 3*a2*(t**2) + 4*a3*(t**3)
        # ddr = 2*a1 + 6*a2*t + 12*a3*(t**2)

        self.r_polynomial = ca.Function('com', [delta_T, t, r0, dr0, r1, dr1], [r, dr, ddr], 
                                        ['delta_T', 't', 'r0', 'dr0', 'r1', 'dr1'], ['r', 'dr', 'ddr'])

    def setPolyCoefficients(self):
        # Set Base coefficients
        self.contact_bool = []
        for step in range(self.num_phases):
            t = 0
            # print(self.knot_points, self.knot_points/self.num_phases)
            
            self.time_phases.append(self.opti.variable(1))
            self.opti.subject_to(self.time_phases[-1] > 0)
            self.opti.set_initial(self.time_phases[-1], self.total_duration/self.num_phases)

            # self.r_variables.append(self.opti.variable(2))
            # self.r_dot_variables.append(self.opti.variable(2))

            # r0, dr0 = self.r_variables[-1], self.r_dot_variables[-1]

            # self.r_variables.append(self.opti.variable(2))
            # self.r_dot_variables.append(self.opti.variable(2))
            # r1, dr1 = self.r_variables[-1], self.r_dot_variables[-1]

            # self.q_variables.append(self.opti.variable(3))
            # self.q_dot_variables.append(self.opti.variable(3))
            # q0, dq0 = self.q_variables[-1], self.q_dot_variables[-1]

            # self.q_variables.append(self.opti.variable(3))
            # self.q_dot_variables.append(self.opti.variable(3))
            # q1, dq1 = self.q_variables[-1], self.q_dot_variables[-1]

            if step == 0:
                self.f_variables.append(self.opti.variable(2))
                self.f_dot_variables.append(self.opti.variable(2))
                f0, df0 = self.f_variables[-1], self.f_dot_variables[-1]

                self.p_variables.append(self.opti.variable(2))
                self.p_dot_variables.append(self.opti.variable(2))
                p0, dp0 = self.p_variables[-1], self.p_dot_variables[-1]

                self.f_variables.append(self.opti.variable(2))
                self.f_dot_variables.append(self.opti.variable(2))
                f1, df1 = self.f_variables[-1], self.f_dot_variables[-1]

                self.p_variables.append(self.opti.variable(2))
                self.p_dot_variables.append(self.opti.variable(2))
                p1, dp1 = self.p_variables[-1], self.p_dot_variables[-1]
            else:
                f0, df0 = self.f_variables[-1], self.f_dot_variables[-1]
                p0, dp0 = self.p_variables[-1], self.p_dot_variables[-1]

                self.f_variables.append(self.opti.variable(2))
                self.f_dot_variables.append(self.opti.variable(2))
                f1, df1 = self.f_variables[-1], self.f_dot_variables[-1]

                self.p_variables.append(self.opti.variable(2))
                self.p_dot_variables.append(self.opti.variable(2))
                p1, dp1 = self.p_variables[-1], self.p_dot_variables[-1]
                
            delta_T = self.time_phases[-1]

            for n in range(self.knot_points):

                if step%2 == 0:
                    self.contact_bool.append('True')
                else:
                    self.contact_bool.append('False')


                ############################################################
                if n == 0:
                    self.r_variables.append(self.opti.variable(2))
                    self.r_dot_variables.append(self.opti.variable(2))
                    r0, dr0 = self.r_variables[-1], self.r_dot_variables[-1]
                else:
                    r0, dr0 = self.r_variables[-1], self.r_dot_variables[-1]
                
                self.r_variables.append(self.opti.variable(2))
                self.r_dot_variables.append(self.opti.variable(2))
                r1, dr1 = self.r_variables[-1], self.r_dot_variables[-1]
                            
                # delta_T = self.dt

                r_poly = self.r_polynomial(delta_T=self.dt, t=t, r0=r0, dr0=dr0, r1=r1, dr1=dr1)
                self.r.append(r_poly['r'])
                self.r_dot.append(r_poly['dr'])
                self.r_ddot.append(r_poly['ddr'])

                ############################################################
                if n == 0:
                    self.q_variables.append(self.opti.variable(1))
                    self.q_dot_variables.append(self.opti.variable(1))
                    q0, dq0 = self.q_variables[-1], self.q_dot_variables[-1]
                else:
                    q0, dq0 = self.q_variables[-1], self.q_dot_variables[-1]
                
                self.q_variables.append(self.opti.variable(1))
                self.q_dot_variables.append(self.opti.variable(1))
                q1, dq1 = self.q_variables[-1], self.q_dot_variables[-1]
                            
                # delta_T = self.dt

                q_poly = self.q_polynomial(delta_T=self.dt, t=t, q0=q0, dq0=dq0, q1=q1, dq1=dq1)
                self.q.append(q_poly['q'])
                self.q_dot.append(q_poly['dq'])
                self.q_ddot.append(q_poly['ddq'])

                ###################################################################                                    
                f_poly = self.f_polynomial(delta_T=delta_T, t=t, f0=f0, df0=df0, f1=f1, df1=df1)
                self.f.append(f_poly['f'])
                self.f_dot.append(f_poly['df'])

                ###################################################################                                    
                p_poly = self.p_polynomial(delta_T=delta_T, t=t, p0=p0, dp0=dp0, p1=p1, dp1=dp1)
                self.p.append(p_poly['p'])
                self.p_dot.append(p_poly['dp'])

                t += self.dt

        self.opti.subject_to(sum(self.time_phases) == self.total_duration)
        # print(self.knot_points)
        # print(len(self.q))
        # print(len(self.p))

    def setModelConstraints(self):

        step_checker = 0
        # self.opti.minimize(ca.sumsqr(sum(self.p_dot)) + ca.sumsqr(sum(self.f_dot)))

        self.ceq.append(self.r[-1] == ca.DM([ 1, 1.5*np.max(self.model.length)]))
        self.ceq.append(self.r[0]  == ca.DM([-1, 1.5*np.max(self.model.length)]))
        self.ceq.append(self.q[0] == 0)
        angp = ca.DM([np.pi]*3)
        angn = ca.DM([-np.pi]*3)
        # jump_start = 0

        # for n in range(len(self.r)-1):
        #     self.model.setState(self.r[n], self.q[n], 
        #                         self.p[n], self.f[n])
            
        #     ddr1 = self.model.dynamic_constraints['r_ddot']
        #     ddq1 = self.model.dynamic_constraints['q_ddot']
            
        #     self.model.setState(self.r[n+1], self.q[n+1], 
        #                         self.p[n+1], self.f[n+1])


        #     ddr2 = self.model.dynamic_constraints['r_ddot']
        #     ddq2 = self.model.dynamic_constraints['q_ddot']

        #     self.ceq.append( (ddr1 + ddr2)*self.dt/2== self.r_dot[n+1] - self.r_dot[n])
        #     self.ceq.append( (ddq1 + ddq2)*self.dt/2== self.q_dot[n+1] - self.q_dot[n])
            
        #     self.ceq.append( (self.r_dot[n+1] + self.r_dot[n])*self.dt/2== self.r[n+1] - self.r[n])
        #     self.ceq.append( (self.q_dot[n+1] + self.q_dot[n])*self.dt/2== self.q[n+1] - self.q[n])

        for n in range(len(self.r)):
    
            # Body Constraints    
            self.model.setState(self.r[n], self.q[n], 
                                self.p[n], self.f[n])


            # self.ceq.append((self.model.kinematic_constraint['constraint']) <= self.model.b)
            
            # self.ceq.append(self.model.dynamic_constraints['r_ddot'] == self.r_ddot[n])
            # self.ceq.append(self.model.dynamic_constraints['q_ddot'] == self.q_ddot[n])
            
            # print(self.model.q.shape, n)
            
            self.ciq.append(self.model.q<= angp)
            self.ciq.append(self.model.q>= angn)
            
            kin_constr = self.model.kinematic_model(r=self.r[n], q=self.q[n], pe=self.p[n])
            dyn_constr = self.model.dynamic_model(r=self.r[n], pe=self.p[n], f=self.f[n])

            # self.ciq.append(ca.fabs(kin_constr['constraint'])[0] < self.model.b[0])
            # self.ciq.append(ca.fabs(kin_constr['constraint'])[1] < self.model.b[1])
            self.ciq.append((self.r[n]-self.p[n])<self.model.nominal_pe+self.model.b)
            self.ciq.append((self.r[n]-self.p[n])>self.model.nominal_pe-self.model.b)

            # self.ciq.append((self.r[n][1]-self.p[n][1])>0)

            self.ceq.append(dyn_constr['r_ddot'][0] == self.r_ddot[n][0])
            self.ceq.append(dyn_constr['r_ddot'][1] == self.r_ddot[n][1])
            self.ceq.append(dyn_constr['q_ddot'] == self.q_ddot[n])

            # Environmental Constraints
            # if n%int(self.num_phases) == 0 and n > 0:
            #     jump_start = 1

            # if n%int(self.num_phases) == 0:
            #     self.ceq.append(self.r_dot[n] == 0)
            #     self.ceq.append(self.q_dot[n] == 0)
            #     # self.ceq.append(self.p_dot[n] == 0)
            #     self.ceq.append(self.f_dot[n] == 0)

            #     # last_p = self.p[n]

            # self.ceq.append(self.f[n]*self.p[n] == 0)
            self.ciq.append( (self.r[n][1,0] - self.model.nominal_pe[1,0]) >= self.terrain.heightMap(self.r[n][1,0] - self.model.nominal_pe[1,0])) # com above ground

            if self.contact_bool[n] == 'False': # no contact
                self.ceq.append(self.f[n] == 0) # foot force = 0
                self.ceq.append(self.f_dot[n] == 0) # foot force = 0
                # self.ciq.append( self.r[n][1,0]>self.terrain.heightMap(self.r[n][0,0])) # com above ground
                self.ciq.append( self.p[n][1,0]>self.terrain.heightMap(self.p[n][0,0])) # com above ground
                # self.ciq.append( (self.p[n][1,0]**2)>0) 
            else: # contact
                self.ciq.append(ca.sumsqr(self.f[n]) <= ca.sumsqr(np.sum(self.model.mass)*self.model.gravity_vector))
                self.ciq.append((ca.fabs(self.terrain.mu*self.f[n][0,0])) - self.f[n][1,0] >= 0) # friction
                # self.ciq.append(ca.dot(self.f[n],self.terrain.heightMapNormalVector(self.model.pe[0,0])) >= ca.fabs(ca.dot(self.f[n],self.terrain.heightMapTangentVector(self.model.pe[0,0])))) # friction
                self.ciq.append(ca.dot(self.f[n],self.terrain.heightMapNormalVector(self.p[n][0,0])) >= 0) # pushing force
                self.ceq.append( self.p[n][1,0]==self.terrain.heightMap(self.p[n][0,0])) # foot not moving
                # self.ceq.append( self.r[n][1,0]>=self.terrain.heightMap(self.r[n][0,0])) # com above ground
                # self.ceq.append( self.model.pe[1,0]==0) # foot not moving
                self.ceq.append(self.p_dot[n]==0) # no slip

    def setConstraints(self):
        self.setModelConstraints()
        self.opti.subject_to(self.ceq)
        self.opti.subject_to(self.ciq)

    def setInitialGuess(self):

        step_checker = 0
        # self.opti.minimize(ca.sumsqr(sum(self.p_dot)) + ca.sumsqr(sum(self.f_dot)))
        angp = ca.DM([np.pi/2]*3)
        angn = ca.DM([-np.pi/2]*3)
        jump_start = 0
        for n in range(len(self.r_variables)):
            self.opti.bounded(angn, self.q_variables[n], angp)

            self.opti.set_initial(self.r_variables[n][0], (2*n)/(self.knot_points-1))            
            self.opti.set_initial(self.q_variables[n][0], (2*n)/(self.knot_points-1))
            
    ######################################################################

    # def setPolynomial(self):
    #     delta_T = ca.MX.sym('delta_T',1)
    #     t = ca.MX.sym('t', 1)

    #     ############################################################
    #     # p0  = ca.MX.sym( 'p0_1', 2)
    #     # p1  = ca.MX.sym( 'p1_1', 2)
    #     # dp0 = ca.MX.sym('dp0_1', 2)
    #     # dp1 = ca.MX.sym('dp1_1', 2)

    #     # a0 = p0
    #     # a1 = dp0
    #     # a2 = -(delta_T**(-2))*(3*(p0 - p1) + delta_T*(2*dp0 + dp1))
    #     # a3 = (delta_T**(-3))*(2*(p0 - p1) + delta_T*(dp0 + dp1))

    #     # p = a0 + a1*t + a2*(t**2) + a3*(t**3)
    #     # dp = a1 + 2*a2*t + 3*a3*(t**2)

    #     # self.p_polynomial = ca.Function('end_effector', [delta_T, t, p0, dp0, p1, dp1], [p, dp], 
    #     #                                 ['delta_T', 't', 'p0', 'dp0', 'p1', 'dp1'], ['p', 'dp'])

    #     ############################################################
    #     f0  = ca.MX.sym( 'f0_1', 2)
    #     f1  = ca.MX.sym( 'f1_1', 2)
    #     df0 = ca.MX.sym('df0_1', 2)
    #     df1 = ca.MX.sym('df1_1', 2)

    #     a0 = f0
    #     a1 = df0
    #     a2 = -(delta_T**(-2))*(3*(f0 - f1) + delta_T*(2*df0 + df1))
    #     a3 = (delta_T**(-3))*(2*(f0 - f1) + delta_T*(df0 + df1))

    #     f = a0 + a1*t + a2*(t**2) + a3*(t**3)
    #     df = a1 + 2*a2*t + 3*a3*(t**2)

    #     self.f_polynomial = ca.Function('force', [delta_T, t, f0, df0, f1, df1], [f, df], 
    #                                     ['delta_T', 't', 'f0', 'df0', 'f1', 'df1'], ['f', 'df'])

    #     ############################################################
    #     q0  = ca.MX.sym( 'q0_1', 3)
    #     q1  = ca.MX.sym( 'q1_1', 3)
    #     dq0 = ca.MX.sym('dq0_1', 3)
    #     dq1 = ca.MX.sym('dq1_1', 3)

    #     a0 = q0
    #     a1 = dq0
    #     a2 = -(delta_T**(-2))*(3*(q0 - q1) + delta_T*(2*dq0 + dq1))
    #     a3 = (delta_T**(-3))*(2*(q0 - q1) + delta_T*(dq0 + dq1))

    #     q   = a0 + a1*t + a2*(t**2) + a3*(t**3)
    #     dq  = a1 + 2*a2*t + 3*a3*(t**2)
    #     ddq = 2*a2 + 6*a3*t
    #     self.q_polynomial = ca.Function('joint_angles', [delta_T, t, q0, dq0, q1, dq1], [q, dq, ddq], 
    #                                     ['delta_T', 't', 'q0', 'dq0', 'q1', 'dq1'], ['q', 'dq', 'ddq'])

    #     ############################################################
    #     r0  = ca.MX.sym( 'r0_1', 2)
    #     r1  = ca.MX.sym( 'r1_1', 2)
    #     dr0 = ca.MX.sym('dr0_1', 2)
    #     dr1 = ca.MX.sym('dr1_1', 2)

    #     a0 = r0
    #     a1 = dr0
    #     a2 = -(delta_T**(-2))*(3*(r0 - r1) + delta_T*(2*dr0 + dr1))
    #     a3 = (delta_T**(-3))*(2*(r0 - r1) + delta_T*(dr0 + dr1))

    #     r   = a0 + a1*t + a2*(t**2) + a3*(t**3)
    #     dr  = a1 + 2*a2*t + 3*a3*(t**2)
    #     ddr = 2*a2 + 6*a3*t

    #     self.r_polynomial = ca.Function('com', [delta_T, t, r0, dr0, r1, dr1], [r, dr, ddr], 
    #                                     ['delta_T', 't', 'r0', 'dr0', 'r1', 'dr1'], ['r', 'dr', 'ddr'])

    # def setPolyCoefficients(self):
    #     # Set Base coefficients
    #     t = 0
    #     # print(self.knot_points, self.knot_points/self.num_phases)
    #     for n in range(self.knot_points):
    #         if n%int((self.knot_points-1)/self.num_phases) == 0:
    #             self.time_phases.append(self.opti.variable(1))
    #             self.opti.subject_to(self.time_phases[-1] > 0)
    #             self.opti.set_initial(self.time_phases[-1], self.total_duration/self.num_phases)
    #             delta_T = self.time_phases[-1]/(self.knot_points/self.num_phases)

    #         ############################################################
    #         if n == 0:
    #             self.r_variables.append(self.opti.variable(2))
    #             self.r_dot_variables.append(self.opti.variable(2))
    #             r0, dr0 = self.r_variables[-1], self.r_dot_variables[-1]
    #         else:
    #             r0, dr0 = self.r_variables[-1], self.r_dot_variables[-1]
            
    #         self.r_variables.append(self.opti.variable(2))
    #         self.r_dot_variables.append(self.opti.variable(2))
    #         r1, dr1 = self.r_variables[-1], self.r_dot_variables[-1]
                        
    #         # delta_T = self.dt

    #         r_poly = self.r_polynomial(delta_T=delta_T, t=t, r0=r0, dr0=dr0, r1=r1, dr1=dr1)
    #         self.r.append(r_poly['r'])
    #         self.r_dot.append(r_poly['dr'])
    #         self.r_ddot.append(r_poly['ddr'])

    #         ############################################################
    #         if n == 0:
    #             self.q_variables.append(self.opti.variable(3))
    #             self.q_dot_variables.append(self.opti.variable(3))
    #             q0, dq0 = self.q_variables[-1], self.q_dot_variables[-1]
    #         else:
    #             q0, dq0 = self.q_variables[-1], self.q_dot_variables[-1]
            
    #         self.q_variables.append(self.opti.variable(3))
    #         self.q_dot_variables.append(self.opti.variable(3))
    #         q1, dq1 = self.q_variables[-1], self.q_dot_variables[-1]
                        
    #         # delta_T = self.dt

    #         q_poly = self.q_polynomial(delta_T=delta_T, t=t, q0=q0, dq0=dq0, q1=q1, dq1=dq1)
    #         self.q.append(q_poly['q'])
    #         self.q_dot.append(q_poly['dq'])
    #         self.q_ddot.append(q_poly['ddq'])

    #         ############################################################
    #         # if n == 0:
    #         #     self.p_variables.append(self.opti.variable(2))
    #         #     self.p_dot_variables.append(self.opti.variable(2))
    #         #     p0, dp0 = self.p_variables[-1], self.p_dot_variables[-1]
    #         # else:
    #         #     p0, dp0 = self.p_variables[-1], self.p_dot_variables[-1]
            
    #         # self.p_variables.append(self.opti.variable(2))
    #         # self.p_dot_variables.append(self.opti.variable(2))
    #         # p1, dp1 = self.p_variables[-1], self.p_dot_variables[-1]
                        
    #         # if n%int(self.knot_points/self.num_phases) == 0:
    #         #     self.time_phases.append(self.opti.variable(1))
    #         #     self.opti.subject_to(self.time_phases[-1] > 0)
    #         #     self.opti.set_initial(self.time_phases[-1], self.total_duration/self.num_phases)
    #         #     delta_T = self.time_phases[-1]/(self.knot_points/self.num_phases)

    #         # p_poly = self.p_polynomial(delta_T=delta_T, t=t, p0=p0, dp0=dp0, p1=p1, dp1=dp1)
    #         # self.p.append(p_poly['p'])
    #         # self.p_dot.append(p_poly['dp'])

    #         ############################################################

    #         if n == 0:
    #             self.f_variables.append(self.opti.variable(2))
    #             self.f_dot_variables.append(self.opti.variable(2))
    #             f0, df0 = self.f_variables[-1], self.f_dot_variables[-1]
    #         else:
    #             f0, df0 = self.f_variables[-1], self.f_dot_variables[-1]
            
    #         self.f_variables.append(self.opti.variable(2))
    #         self.f_dot_variables.append(self.opti.variable(2))
    #         f1, df1 = self.f_variables[-1], self.f_dot_variables[-1]
                        
    #         if n%int(self.knot_points/self.num_phases) == 0:
    #             self.time_phases.append(self.opti.variable(1))
    #             self.opti.subject_to(self.time_phases[-1] > 0)
    #             self.opti.set_initial(self.time_phases[-1], self.total_duration/self.num_phases)
    #             delta_T = self.time_phases[-1]/(self.knot_points/self.num_phases)

    #         f_poly = self.f_polynomial(delta_T=delta_T, t=t, f0=f0, df0=df0, f1=f1, df1=df1)
    #         self.f.append(f_poly['f'])
    #         self.f_dot.append(f_poly['df'])

    #         t += self.dt

    #     self.opti.subject_to(sum(self.time_phases) == self.total_duration)
    #     # print(self.knot_points)
    #     # print(len(self.q))
    #     # print(len(self.p))

    # def setModelConstraints(self):

    #     step_checker = 0
    #     # self.opti.minimize(ca.sumsqr(sum(self.p_dot)) + ca.sumsqr(sum(self.f_dot)))
    #     for n in range(self.knot_points):
    #         # Boundary Constraints
    #         if n==0:
    #             self.ceq.append(self.r[n] == ca.DM([0,0]))
    #             self.ceq.append(self.q[n] == 0)
    #         if n==self.knot_points-1:
    #             print('hello')
    #             self.ceq.append(self.r[n] == ca.DM([0,0]))
                
    #         # Body Constraints    
    #         self.model.setState(self.r[n], self.r_dot[n], 
    #                             self.q[n], self.q_dot[n], self.f[n])
    #         # self.ceq.append(ca.norm_2(self.model.kinematic_constraints['constraint violation']) == 0)
    #         self.ceq.append(self.model.dynamic_constraints['r_ddot'] == self.r_ddot[n])
    #         self.ceq.append(self.model.dynamic_constraints['q_ddot'] == self.q_ddot[n])

    #         # Environmental Constraints
    #         if n%int(self.knot_points/self.num_phases) == 0 and n > 0:
    #             step_checker += 1

    #         if n%int(self.knot_points/self.num_phases) == 0:
    #             self.ceq.append(self.r_dot[n] == 0)
    #             self.ceq.append(self.q_dot[n] == 0)
    #             # self.ceq.append(self.p_dot[n] == 0)
    #             self.ceq.append(self.f_dot[n] == 0)

    #             # last_p = self.p[n]

    #         if step_checker%2 != 0: # no contact
    #             self.ceq.append(self.f[n] == 0) # foot force = 0
    #             self.ciq.append(self.terrain.heightMap(self.model.pe[0,0]) <= self.model.pe[1,0]) # pe_y > ground
    #         else: # contact
    #             # self.ciq.append((ca.fabs(self.terrain.mu*self.f[n][0,0]) - self.f[n][1,0]) >= 0) # friction
    #             # self.ciq.append(ca.dot(self.f[n],self.terrain.heightMapNormalVector(self.model.pe[0,0])) >= ca.fabs(ca.dot(self.f[n],self.terrain.heightMapTangentVector(self.model.pe[0,0])))) # friction
    #             self.ciq.append(ca.dot(self.f[n],self.terrain.heightMapNormalVector(self.model.pe[0,0])) >= 0) # pushing force
    #             self.ceq.append( self.model.pe[1,0]==self.terrain.heightMap(self.model.pe[0,0])) # foot not moving
    #             self.ceq.append( self.terrain.heightMap(self.model.pe[0,0]) == self.model.pe[1,0]) # foot not moving
    #             # self.ceq.append(self.p_dot[n]==0) # no slip

    # def setConstraints(self):
    #     self.setModelConstraints()
    #     self.opti.subject_to(self.ceq)
    #     self.opti.subject_to(self.ciq)

    # def setInitialGuess(self):

    #     step_checker = 0
    #     for n in range(self.knot_points):
    #         self.opti.bounded(3*[-np.pi/2], self.q_variables[n], 3*[np.pi/2])

    #         self.opti.set_initial(self.r_variables[n][0], (2*n)/(self.knot_points-1))            
    #         self.opti.set_initial(self.q_variables[n][0], (2*n)/(self.knot_points-1))
    #         # self.opti.set_initial(self.p_variables[n][0], (2*n)/(self.knot_points-1))

    #         # if n%int(self.knot_points/self.num_phases) == 0 and n > 0:
    #         #     step_checker += 1

    #         # if step_checker%2 != 0: # no contact
    #         #     self.opti.set_initial(self.f_variables[n][0], 0)
    #         # #     self.opti.set_initial(self.p_variables[n][0], (2*n)/(self.knot_points-1))
    #         # #     self.opti.set_initial(self.p_variables[n][1], (2*(n-(2*(self.knot_points-1)/3)))*(n-((self.knot_points-1)/3))/(self.knot_points-1))
    #         # else: # contact
    #         #     # self.opti.set_initial(self.p_dot_variables[n][0], (2)/(self.knot_points-1))
    #         #     self.opti.set_initial(self.f_variables[n][0], self.model.gravity*self.model.mcom)
    #             # self.opti.set_initial(self.p_variables[n], 2*[0])



    # def plotCallback(self):
    #     fig = plt.figure()
    #     ax = fig.add_subplot(111)
    #     ax.grid()

    #     def callplot(p):
    #         plt.cla()
    #         ax.grid()
    #         # ax.set_xlim([-2, 2])
    #         # ax.set_ylim([-2, 2])

    #         # temp = ca.DM.zeros(2,3)

    #         # temp[0,0],temp[1,0] = self.model.length[0]*ca.sin(q0[0]) + p0[0,0]  , self.model.length[0]*ca.cos(q0[0]) + p0[1,0]
    #         # temp[0,1],temp[1,1] = self.model.length[1]*ca.sin(q0[1]) + temp[0,0], self.model.length[1]*ca.cos(q0[1]) + temp[1,0]
    #         # temp[0,2],temp[1,2] = self.model.length[2]*ca.sin(q0[2]) + temp[0,1], self.model.length[2]*ca.cos(q0[2]) + temp[1,1]

    #         # ax.plot([p0[0,0], temp[0,0]], [p0[1,0], temp[1,0]], 'r', lw=4)
    #         # ax.plot([temp[0,0], temp[0,1]], [temp[1,0], temp[1,1]], 'g', lw=4)
    #         # ax.plot([temp[0,1], temp[0,2]], [temp[1,1], temp[1,2]], 'b', lw=10)
    #         ax.plot(self.time, p, 'bo')
    #         plt.draw()
    #         plt.pause(1e-5)

    #     p = ca.MX.zeros(2, self.knot_points)
    #     for n in range(self.knot_points):
    #         p[:,n] = self.p[n]
    #     self.opti.callback(lambda x : callplot(opti.debug.value(p)))


    # Old code

    def setSpline(self):
        q_variables     = []
        q_dot_variables = []
        r_variables     = []
        r_dot_variables = []
        p_variables     = []
        p_dot_variables = []
        f_dot_variables = []
        f_variables     = []
        t = ca.MX.sym('t', 1)
        delta_T = ca.MX.sym('delta_T',1)

        r_poly = []
        ############################################################
        for n in range(self.knot_points):
            if n == 0:
                r_variables.append(    ca.MX.sym( 'r0'+str(n),2,1))
                r_dot_variables.append(ca.MX.sym('dr0'+str(n),2,1))
                r0, dr0 = r_variables[-1], r_dot_variables[-1]
            else:
                r0, dr0 = r_variables[-1], r_dot_variables[-1]
            
            r_variables.append(    ca.MX.sym( 'r1'+str(n),2,1))
            r_dot_variables.append(ca.MX.sym('dr1'+str(n),2,1))
            r1, dr1 = r_variables[-1], r_dot_variables[-1]

            r_poly.append(self.r_polynomial(delta_T=delta_T, t=t, r0=r0, dr0=dr0, r1=r1, dr1=dr1)['r'])

        input_variables = [delta_T, t]
        r_variables.extend(r_dot_variables)
        input_variables.extend(r_variables)
        self.r_spline = ca.Function('com', input_variables, r_poly)

        t = 0
        delta_T = self.dt

        q_variables     = []
        q_dot_variables = []
        r_variables     = []
        r_dot_variables = []
        p_variables     = []
        p_dot_variables = []
        f_dot_variables = []
        f_variables     = []

        r_poly = []
        ############################################################
        for n in range(self.knot_points):
            if n == 0:
                r_variables.append(    ca.DM([2,1]))
                r_dot_variables.append(ca.DM([0,0]))
                r0, dr0 = r_variables[-1], r_dot_variables[-1]
            else:
                r0, dr0 = r_variables[-1], r_dot_variables[-1]
            
            r_variables.append(    ca.DM([2,1]))
            r_dot_variables.append(ca.DM([0,0]))
            r1, dr1 = r_variables[-1], r_dot_variables[-1]
            
            r_poly.append(self.r_polynomial(delta_T=delta_T, t=t, r0=r0, dr0=dr0, r1=r1, dr1=dr1)['r'])
            t += delta_T

        input_variables = [delta_T, t]
        r_variables.extend(r_dot_variables)
        input_variables.extend(r_variables)
        r_spline = self.r_spline(*input_variables)

        print(r_poly)
        print('\n')
        print(r_spline)

    def contructPhaseSpline(self):
        delta_T = ca.MX.sym('delta_T',1)
        t = ca.MX.sym('t', 1)

        x0  = ca.MX.sym( 'x0_1', 2)
        x1  = ca.MX.sym( 'x1_1', 2)
        dx0 = ca.MX.sym('dx0_1', 2)
        dx1 = ca.MX.sym('dx1_1', 2)

        a0 = x0
        a1 = dx0
        a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
        a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

        x = a0 + a1*t + a2*(t**2) + a3*(t**3)
        dx = a1 + 2*a2*t + 3*a3*(t**2)

        f = ca.Function('f', [delta_T, t, x0, dx0, x1, dx1], [x], ['delta_T', 't', 'x0', 'dx0', 'x1', 'dx1'], ['x'])
        df = ca.Function('f', [delta_T, t, x0, dx0, x1, dx1], [dx], ['delta_T', 't', 'x0', 'dx0', 'x1', 'dx1'], ['dx'])

        T = ca.MX.sym('T',1)
        delta_T = T/3
        x0_1  = x0  
        x1_1  = x1  
        dx0_1 = dx0 
        dx1_1 = dx1 

        x0_2  = x1_1
        x1_2  = ca.MX.sym( 'x1_2', 2)
        dx0_2 = dx1_1
        dx1_2 = ca.MX.sym('dx1_2', 2)

        x0_3  = x1_2
        x1_3  = ca.MX.sym( 'x1_3', 2)
        dx0_3 = dx1_2
        dx1_3 = ca.MX.sym('dx1_3', 2)

        for i in range(3):
            if i == 0:
                x0  =  x0_1
                x1  =  x1_1
                dx0 = dx0_1
                dx1 = dx1_1
                y1  = f(delta_T=delta_T, t=t, x0=x0, dx0=dx0, x1=x1, dx1=dx1)['x']
                dy1 = df(delta_T=delta_T, t=t, x0=x0, dx0=dx0, x1=x1, dx1=dx1)['dx']
            elif i == 1:
                x0  =  x0_2 
                x1  =  x1_2 
                dx0 = dx0_2
                dx1 = dx1_2
                y2  = f(delta_T=delta_T, t=t, x0=x0, dx0=dx0, x1=x1, dx1=dx1)['x']
                dy2 = df(delta_T=delta_T, t=t, x0=x0, dx0=dx0, x1=x1, dx1=dx1)['dx']
            else:
                x0  =  x0_3 
                x1  =  x1_3 
                dx0 = dx0_3
                dx1 = dx1_3
                y3  = f(delta_T=delta_T, t=t, x0=x0, dx0=dx0, x1=x1, dx1=dx1)['x']
                dy3 = df(delta_T=delta_T, t=t, x0=x0, dx0=dx0, x1=x1, dx1=dx1)['dx']

        self.phase_spline = ca.Function("F", [T, t, x0_1, dx0_1, x1_1, dx1_1,
                                              x1_2, dx1_2, x1_3, dx1_3], [y1, y2, y3], 
                                              ['T', 't', 'x0_1', 'dx0_1', 'x1_1', 'dx1_1',
                                              'x1_2', 'dx1_2', 'x1_3', 'dx1_3'], ['y1', 'y2', 'y3'])
        
        self.dphase_spline = ca.Function("F", [T, t, x0_1, dx0_1, x1_1, dx1_1,
                                              x1_2, dx1_2, x1_3, dx1_3], [dy1, dy2, dy3], 
                                              ['T', 't', 'x0_1', 'dx0_1', 'x1_1', 'dx1_1',
                                              'x1_2', 'dx1_2', 'x1_3', 'dx1_3'], ['dy1', 'dy2', 'dy3'])

    def setPhaseSpline(self, delta_T, t, x0_1, x1_1, x1_2, x1_3, dx0_1, dx1_1, dx1_2, dx1_3):
        p0_1 ,  f0_1 = x0_1 
        p1_1 ,  f1_1 = x1_1 
        p1_2 ,  f1_2 = x1_2 
        p1_3 ,  f1_3 = x1_3 
        dp0_1, df0_1 = dx0_1
        dp1_1, df1_1 = dx1_1
        dp1_2, df1_2 = dx1_2
        dp1_3, df1_3 = dx1_3

        p0_2 ,  f0_2 =  p1_1,  f1_1 
        dp0_2, df0_2 = dp1_1, df1_1
        p0_3 ,  f0_3 =  p1_2,  f1_2 
        dp0_3, df0_3 = dp1_2, df1_2

        for i in range(3):
            if i == 0:
                x0  =  p0_1
                x1  =  p1_1
                dx0 = dp0_1
                dx1 = dp1_1
                
                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                p1 = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dp1 = a1 + 2*a2*t + 3*a3*(t**2)

                #################################################################

                x0  =  f0_1
                x1  =  f1_1
                dx0 = df0_1
                dx1 = df1_1
                
                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                f1 = a0 + a1*t + a2*(t**2) + a3*(t**3)
                df1 = a1 + 2*a2*t + 3*a3*(t**2)


            elif i == 1:
                x0  =  p0_2 
                x1  =  p1_2 
                dx0 = dp0_2
                dx1 = dp1_2

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                p2 = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dp2 = a1 + 2*a2*t + 3*a3*(t**2)

                #################################################################

                x0  =  f0_2 
                x1  =  f1_2 
                dx0 = df0_2
                dx1 = df1_2

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                f2 = a0 + a1*t + a2*(t**2) + a3*(t**3)
                df2 = a1 + 2*a2*t + 3*a3*(t**2)

            else:
                x0  =  p0_3 
                x1  =  p1_3 
                dx0 = dp0_3
                dx1 = dp1_3

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                p3 = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dp3 = a1 + 2*a2*t + 3*a3*(t**2)

                #################################################################

                x0  =  f0_3 
                x1  =  f1_3 
                dx0 = df0_3
                dx1 = df1_3

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                f3 = a0 + a1*t + a2*(t**2) + a3*(t**3)
                df3 = a1 + 2*a2*t + 3*a3*(t**2)

        return [p1,p2,p3], [dp1,dp2,dp3], [f1,f2,f3]
    
    def setBaseSpline(self, delta_T, t, x0_1, x1_1, x1_2, x1_3, dx0_1, dx1_1, dx1_2, dx1_3):
        r0_1 ,  q0_1 =  x0_1 
        r1_1 ,  q1_1 =  x1_1 
        r1_2 ,  q1_2 =  x1_2 
        r1_3 ,  q1_3 =  x1_3 
        dr0_1, dq0_1 = dx0_1
        dr1_1, dq1_1 = dx1_1
        dr1_2, dq1_2 = dx1_2
        dr1_3, dq1_3 = dx1_3

        r0_2 ,  q0_2 =  r1_1,  q1_1 
        dr0_2, dq0_2 = dr1_1, dq1_1
        r0_3 ,  q0_3 =  r1_2,  q1_2 
        dr0_3, dq0_3 = dr1_2, dq1_2

        for i in range(3):
            if i == 0:
                x0  =  r0_1
                x1  =  r1_1
                dx0 = dr0_1
                dx1 = dr1_1
                
                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                r1   = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dr1  = a1 + 2*a2*t + 3*a3*(t**2)
                ddr1 = 2*a2 + 6*a3*t

                #################################################################

                x0  =  q0_1
                x1  =  q1_1
                dx0 = dq0_1
                dx1 = dq1_1
                
                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                q1   = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dq1  = a1 + 2*a2*t + 3*a3*(t**2)
                ddq1 = 2*a2 + 6*a3*t


            elif i == 1:
                x0  =  r0_2 
                x1  =  r1_2 
                dx0 = dr0_2
                dx1 = dr1_2

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                r2   = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dr2  = a1 + 2*a2*t + 3*a3*(t**2)
                ddr2 = 2*a2 + 6*a3*t

                #################################################################

                x0  =  q0_2 
                x1  =  q1_2 
                dx0 = dq0_2
                dx1 = dq1_2

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                q2   = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dq2  = a1 + 2*a2*t + 3*a3*(t**2)
                ddq2 = 2*a2 + 6*a3*t

            else:
                x0  =  r0_3 
                x1  =  r1_3 
                dx0 = dr0_3
                dx1 = dr1_3

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                r3   = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dr3  = a1 + 2*a2*t + 3*a3*(t**2)
                ddr3 = 2*a2 + 6*a3*t

                #################################################################

                x0  =  q0_3 
                x1  =  q1_3 
                dx0 = dq0_3
                dx1 = dq1_3

                a0 = x0
                a1 = dx0
                a2 = -(delta_T**(-2))*(3*(x0 - x1) + delta_T*(2*dx0 + dx1))
                a3 = (delta_T**(-3))*(2*(x0 - x1) + delta_T*(dx0 + dx1))

                q3   = a0 + a1*t + a2*(t**2) + a3*(t**3)
                dq3  = a1 + 2*a2*t + 3*a3*(t**2)
                ddq3 = 2*a2 + 6*a3*t

        return [r1,r2,r3], [dr1,dr2,dr3], [ddr1,ddr2,ddr3], [q1,q2,q3], [dq1,dq2,dq3], [ddq1,ddq2,ddq3]

    def setVariables(self):
        N = self.phase_knot_points
        for phase in range(self.num_phases):
            # parametrize phase spline for feet and force
            self.time_phases.append(self.opti.variable(1))
            delta_T = self.time_phases[-1]

            self.ciq.append(delta_T>=0) # time is positive
            self.opti.set_initial(delta_T, self.total_duration/self.num_phases)
            
            t = 0

            p1_2 ,  f1_2 = self.opti.variable(2), self.opti.variable(2) # ' p1_2 ', 'f1_2'
            dp1_2, df1_2 = self.opti.variable(2), self.opti.variable(2) # 'dp1_2', 'df1_2'
            p1_3 ,  f1_3 = self.opti.variable(2), self.opti.variable(2) # ' p1_3 ', 'f1_3'
            dp1_3, df1_3 = self.opti.variable(2), self.opti.variable(2) # 'dp1_3', 'df1_3'
            
            start_p0_1 , start_f0_1  =  p1_2 , f1_2
            start_p1_1 , start_f1_1  =  p1_3 , f1_3
            start_dp0_1, start_df0_1 = dp1_2, df1_2
            start_dp1_1, start_df1_1 = dp1_3, df1_3

            if phase == 0:
                p0_1 ,  f0_1 = self.opti.variable(2), self.opti.variable(2) #  'p0_1',  'f0_1'
                p1_1 ,  f1_1 = self.opti.variable(2), self.opti.variable(2) #  'p1_1',  'f1_1'
                dp0_1, df0_1 = self.opti.variable(2), self.opti.variable(2) # 'dp0_1', 'df0_1'
                dp1_1, df1_1 = self.opti.variable(2), self.opti.variable(2) # 'dp1_1', 'df1_1'
            else:
                p0_1 ,  f0_1 = start_p0_1 , start_f0_1 
                p1_1 ,  f1_1 = start_p1_1 , start_f1_1 
                dp0_1, df0_1 = start_dp0_1, start_df0_1
                dp1_1, df1_1 = start_dp1_1, start_df1_1

            ####################################################################################
            r1_2 ,  q1_2 = self.opti.variable(2), self.opti.variable(1) # ' r1_2 ', 'q1_2'
            dr1_2, dq1_2 = self.opti.variable(2), self.opti.variable(1) # 'dr1_2', 'dq1_2'
            r1_3 ,  q1_3 = self.opti.variable(2), self.opti.variable(1) # ' r1_3 ', 'q1_3'
            dr1_3, dq1_3 = self.opti.variable(2), self.opti.variable(1) # 'dr1_3', 'dq1_3'
            
            start_r0_1 , start_q0_1  =  r1_2 , q1_2
            start_r1_1 , start_q1_1  =  r1_3 , q1_3
            start_dr0_1, start_dq0_1 = dr1_2, dq1_2
            start_dr1_1, start_dq1_1 = dr1_3, dq1_3

            if phase == 0:
                r0_1 ,  q0_1 = self.opti.variable(2), self.opti.variable(1) #  'r0_1',  'q0_1'
                r1_1 ,  q1_1 = self.opti.variable(2), self.opti.variable(1) #  'r1_1',  'q1_1'
                dr0_1, dq0_1 = self.opti.variable(2), self.opti.variable(1) # 'dr0_1', 'dq0_1'
                dr1_1, dq1_1 = self.opti.variable(2), self.opti.variable(1) # 'dr1_1', 'dq1_1'
            else:
                r0_1 ,  q0_1 = start_r0_1 , start_q0_1 
                r1_1 ,  q1_1 = start_r1_1 , start_q1_1 
                dr0_1, dq0_1 = start_dr0_1, start_dq0_1
                dr1_1, dq1_1 = start_dr1_1, start_dq1_1

            # self.ceq.append(dr0_1 == 0)
            # self.ceq.append(dq0_1 == 0)
            # self.ceq.append(dp0_1 == 0)
            # self.ceq.append(df0_1 == 0)

            # self.ceq.append(dr1_3 == 0)
            # self.ceq.append(dq1_3 == 0)
            # self.ceq.append(dp1_3 == 0)
            # self.ceq.append(df1_3 == 0)

            for knot_point in range(self.phase_knot_points):
                # self.r.append(self.opti.variable(2))
                # self.r_dot.append(self.opti.variable(2))

                # self.q.append(self.opti.variable(1))
                # self.q_dot.append(self.opti.variable(1))

                # r     = self.r[-1]
                # r_dot = self.r_dot[-1]
                # q     = self.q[-1]
                # q_dot = self.q_dot[-1]

                ######################################################################################


                #####################################################################################

                # temp_p = list(self.phase_spline(T=delta_T, t=t, x0_1=p0_1, dx0_1=dp0_1, 
                #                                                 x1_1=p1_1, dx1_1=dp1_1,
                #                                                 x1_2=p1_2, dx1_2=dp1_2, 
                #                                                 x1_3=p1_3, dx1_3=dp1_3).values())

                # temp_dp = list(self.dphase_spline(T=delta_T, t=t, x0_1=p0_1, dx0_1=dp0_1, 
                #                                                   x1_1=p1_1, dx1_1=dp1_1,
                #                                                   x1_2=p1_2, dx1_2=dp1_2, 
                #                                                   x1_3=p1_3, dx1_3=dp1_3).values())

                # temp_f = list(self.phase_spline(T=delta_T, t=t, x0_1=f0_1, dx0_1=df0_1, 
                #                                                 x1_1=f1_1, dx1_1=df1_1,
                #                                                 x1_2=f1_2, dx1_2=df1_2, 
                #                                                 x1_3=f1_3, dx1_3=df1_3).values())                                                  

                temp_r, temp_dr, temp_ddr, temp_q, temp_dq, temp_ddq = self.setBaseSpline(self.dt, t, [r0_1, q0_1], [r1_1, q1_1], [r1_2, q1_2], [r1_3, q1_3],
                                                                                  [dr0_1, dq0_1], [dr1_1, dq1_1], [dr1_2, dq1_2], [dr1_3, dq1_3])

                temp_p, temp_dp, temp_f = self.setPhaseSpline(delta_T, t, [p0_1, f0_1], [p1_1, f1_1], [p1_2, f1_2], [p1_3, f1_3],
                                                                          [dp0_1, df0_1], [dp1_1, df1_1], [dp1_2, df1_2], [dp1_3, df1_3])

                if knot_point <= (N-1)/3:
                    pe  = temp_p [0]
                    dpe = temp_dp[0]
                    f   = temp_f [0]
                    
                    r      = temp_r  [0]
                    r_dot  = temp_dr [0]
                    r_ddot = temp_ddr[0]
                    q      = temp_q  [0]
                    q_dot  = temp_dq [0]
                    q_ddot = temp_ddq[0]

                elif (N-1)/3 < knot_point <= 2*(N-1)/3:
                    pe  = temp_p [1]
                    dpe = temp_dp[1]
                    f   = temp_f [1]

                    r      = temp_r  [1]
                    r_dot  = temp_dr [1]
                    r_ddot = temp_ddr[1]
                    q      = temp_q  [1]
                    q_dot  = temp_dq [1]
                    q_ddot = temp_ddq[1]
                else:
                    pe  = temp_p [2]
                    dpe = temp_dp[2]
                    f   = temp_f [2] 

                    r      = temp_r  [2]
                    r_dot  = temp_dr [2]
                    r_ddot = temp_ddr[2]
                    q      = temp_q  [2]
                    q_dot  = temp_dq [2]
                    q_ddot = temp_ddq[2]

                if phase == 0 and knot_point == 0:
                    self.ceq.append(r[0]==0)
                    self.ceq.append(q[0]==0)
                elif phase == self.num_phases-1 and knot_point == self.phase_knot_points - 1:
                    self.ceq.append(r[0]==0.5)


                self.p.append(pe)
                self.dp.append(dpe)
                self.f.append(f)

                self.r.append(r)
                self.r_dot.append(r_dot)
                self.r_ddot.append(r_ddot)
                self.q.append(q)
                self.q_dot.append(q_dot)
                self.q_ddot.append(q_ddot)

                self.model.setState(r, r_dot, q, q_dot, pe, f)
                
                # f = self.model.dynamics_model(r=r, r_dot=r_dot, q=q, q_dot=q_dot, pe=pe, f=f)
                # r_ddot, q_ddot = f['r_ddot'], f['q_ddot']

                self.ciq.append(self.model.r_ddot <= self.r_ddot[-1]);self.ciq.append(self.model.r_ddot >= self.r_ddot[-1])
                self.ciq.append(self.model.q_ddot <= self.q_ddot[-1]);self.ciq.append(self.model.q_ddot >= self.q_ddot[-1])

                # k = self.model.kinematic_model(r=r, r_dot=r_dot, q=q, q_dot=q_dot, pe=pe)
                # self.ciq.append(k['constraint']) # kinematic constraint

                self.ciq.append(self.model.kinematic_model)
                self.ciq.append(self.terrain.heightMap(self.r[-1][0,0]) <= self.r[-1][1,0]) # pe_y > ground
                
                if phase%2 != 0: # no contact
                    self.ceq.append(self.f[-1] == 0) # foot force = 0
                    self.ciq.append(self.terrain.heightMap(self.p[-1][0,0]) <= self.p[-1][1,0]) # pe_y > ground
                else: # contact
                    self.ciq.append((self.terrain.mu*self.f[-1][0])**2 - self.f[-1][1]**2 >= 0) # friction
                    self.ciq.append(ca.dot(self.f[-1],self.p[-1]) >= 0) # pushing force
                    self.ceq.append(self.p[-1][1]==self.terrain.heightMap(self.p[-1][0])) # foot not moving
                    self.ceq.append(self.dp[-1]==0) # no slip

                self.opti.bounded(-np.pi/2,q,np.pi/2)

                t += self.dt

        self.ceq.append(sum(self.time_phases) == self.total_duration)
    
    def setCollocation(self):
        for n in range(len(self.q)-1):
            # self.ceq.append((self.dt/2)*(self.r_dot[n] + self.r_dot[n+1]) == (self.r[n+1] - self.r[n]))
            self.ceq.append((self.dt/2)*(self.r_ddot[n] + self.r_ddot[n+1]) == (self.r_dot[n+1] - self.r_dot[n]))
            
            # self.ceq.append((self.dt/2)*(self.q_dot[n] + self.q_dot[n+1]) == (self.q[n+1] - self.q[n]))
            self.ceq.append((self.dt/2)*(self.q_ddot[n] + self.q_ddot[n+1]) == (self.q_dot[n+1] - self.q_dot[n]))

    def printInfo(self):
        print('####################################')
        print('####################################')

        print('Formulating the Non-linear Program')
        print('\n---------Hyper parameters-----------')
        print('model = ', self.model.name)
        print('terrain = ', self.terrain.name)
        print('dt = ', self.dt)
        print('number of steps = ', self.num_phases)
        print('total duration = ', self.total_duration)
        print('knot points = ', self.knot_points)

        print('\n---------Parameters-----------')
        print('number of      r(t) variables = ', len(self.r),      ', is symbolic = ', self.r[0].is_symbolic())
        print('number of  r_dot(t) variables = ', len(self.r_dot),  ', is symbolic = ', self.r_dot[0].is_symbolic())
        print('number of r_ddot(t) variables = ', len(self.r_ddot), ', is symbolic = ', self.r_ddot[0].is_symbolic())
        
        print('number of      q(t) variables = ', len(self.q),      ', is symbolic = ', self.q[0].is_symbolic())
        print('number of  q_dot(t) variables = ', len(self.q_dot),  ', is symbolic = ', self.q_dot[0].is_symbolic())
        print('number of q_ddot(t) variables = ', len(self.q_ddot), ', is symbolic = ', self.q_ddot[0].is_symbolic())
        
        # print('number of     pe(t) variables = ', len(self.p),     ', is symbolic = ', self.p[0].is_symbolic())
        # print('number of    dpe(t) variables = ', len(self.p_dot), ', is symbolic = ', self.p_dot[0].is_symbolic())
        print('number of      f(t) variables = ', len(self.f),     ', is symbolic = ', self.f[0].is_symbolic())
        
        print('\n---------Constraints----------')

        print('number of equality constraints   = ', len(self.ceq))
        print('number of inequality constraints = ', len(self.ciq))
        print('Total number of constraints      = ', len(self.ceq) + len(self.ciq))
        print('\nFinished the Non-linear Program')

        print('####################################')
        print('####################################')

# test check for sanity

# test_problem = NonlinearProgram(dt=0.05, steps=3, total_duration=2, model='hopper')            

# print(len(test_problem.p))
# print(len(test_problem.q))

























#################################################################
# class NLP():
#     def __init__(self, knot_points_per_phase, steps, total_duration, model='hopper', terrain='flat'):
#         super().__init__()
#         self.knot_points_per_phase = knot_points_per_phase
#         self.num_phases            = steps
#         self.total_duration        = total_duration

#         if model == 'hopper':
#             self.model = Hopper()
#             self.time_phases = {}
        
#         self.terrain = Terrain(type=terrain)

#         self.opti   = ca.Opti()

#         self.q    = {}
#         self.qdot = {}
#         self.u    = {}
#         self.c3   = {} # i = 0
#         self.dc3  = {} # i = 0
#         # self.ddc3 = {} # i = 0
#         self.f10  = {} # i = 0

#         self.ceq = []
#         self.ciq = []

#         self.setVariables()
#         self.setConstraints()
#         self.setBounds()

#     def setVariables(self):    
#         for step in range(self.num_phases):
            
#             self.time_phases.update({str(step) : self.opti.variable(1)})
#             self.ceq.append(0<=self.time_phases[str(step)])

#             self.q.update(   {str(step) : []})
#             self.qdot.update({str(step) : []})

#             self.c3.update(  {str(step) : []})
#             self.dc3.update( {str(step) : []})
#             # self.ddc3.update({str(step) : []})
            
#             self.u.update(   {str(step) : []})
#             self.f10.update( {str(step) : []})

#             for knot_point in range(self.knot_points_per_phase):
#                 self.q   [str(step)].append(self.opti.variable(3))
#                 self.qdot[str(step)].append(self.opti.variable(3))

#                 self.c3  [str(step)].append(self.opti.variable(2))
#                 self.dc3 [str(step)].append(self.opti.variable(2))
#                 # self.ddc3[str(step)].append(self.opti.variable(2))
                
#                 self.u   [str(step)].append(self.opti.variable(2))
#                 self.f10 [str(step)].append(self.opti.variable(2))
                
#                 q    = self.q   [str(step)][-1]  
#                 qdot = self.qdot[str(step)][-1]
#                 u    = self.u   [str(step)][-1]
#                 c3   = self.c3  [str(step)][-1]
#                 dc3  = self.dc3 [str(step)][-1]
#                 # ddc3 = self.ddc3[str(step)][-1]
#                 f10  = self.f10 [str(step)][-1]
            
#                 self.model.setFullState(q=q, dq=qdot, 
#                                         c3=c3, dc3=dc3, 
#                                         u=u, f10=f10)

#                 self.ceq.append(self.model.p['Constraint'])

#                 # self.opti.minimize(c3[1]**2)
#                 # self.opti.minimize(ca.sumsqr(self.model.p['Leg'][1,:]))

#                 for i in range(3):
#                     self.opti.subject_to((self.model.p['Leg'][1,i]) >= self.terrain.heightMap(self.model.p['Leg'][0,:]))                                                 

#                 # if j==0 and n==0:
#                 #     self.setInitialBoundary()
#                 #     com_x = (self.model.c['Left Leg'][0,:]) + (self.model.c['Right Leg'][0,:]) + (self.model.c['Torso'][0,:]) 
#                 #     self.opti.subject_to(com_x==0)
                
#                 # if j==self.num_phases-1 and n==self.num_phases-1:
#                 # com_y = ca.sum1(self.model.c['Leg'][1,:]) 
#                 # self.opti.subject_to(com_y<=self.model.b)
        
#     def setConstraints(self):
#         self.setBoundary()
#         self.setContactConstraints()
#         self.setCollocationContraints()

#         self.opti.subject_to(self.ceq)

#     def setBoundary(self):
#         # self.opti.subject_to(self.q [str(0)][0] == self.model.initial_q)
#         # self.opti.subject_to(self.c3[str(0)][0] == np.zeros((2,1)))
#         # self.opti.subject_to(self.q[str(self.num_phases-1)][-1] == self.model.final_q)
#         # self.opti.subject_to(self.c3[str(self.num_phases-1)][-1][0] == 1)
        
#         self.ceq.append(self.q [str(0)][0] == self.model.initial_q)
#         # self.ceq.append(self.c3[str(0)][0][0,0] == 0)

#     def setContactConstraints(self):

#         # self.opti.subject_to(sum(self.time_phases.values()) == self.total_duration)
#         self.ceq.append(sum(self.time_phases.values()) == self.total_duration)

#         for step in range(self.num_phases):
            
#             # if step is even ==> Contact
#             # if step is odd  ==> No Contact
#             for knot_point in range(self.knot_points_per_phase):
                

#                 # if step > 0:
#                 #     # self.opti.subject_to(self.c3 [str(step-1)][-1] - self. c3[str(step)][0] == 0)
#                 #     # self.opti.subject_to(self.f10[str(step-1)][-1] - self.f10[str(step)][0] == 0)
                    
#                 #     self.ceq.append(self.c3 [str(step-1)][-1] - self.c3 [str(step)][0] == 0)
#                 #     self.ceq.append(self.dc3 [str(step-1)][-1] - self.dc3[str(step)][0] == 0)
#                 #     self.ceq.append(self.f10[str(step-1)][-1] - self.f10[str(step)][0] == 0)
                
#                 if step%2 != 0:
#                     f10 = self.f10[str(step)][knot_point]
#                     c3  = self.c3 [str(step)][knot_point]

#                     # self.opti.bounded(0,self.terrain.heightMap(c3[0])-c3[1],ca.inf)
#                     # self.opti.subject_to(f10==0)
                    
#                     # self.ceq.append(self.terrain.heightMap(c3[0])<=c3[1])   
#                     self.ceq.append(f10==0)
#                 else: 
#                     c3  = self.c3 [str(step)][knot_point]
#                     dc3 = self.dc3[str(step)][knot_point]
#                     f10 = self.f10[str(step)][knot_point]
                    
#                     # self.opti.subject_to((self.terrain.mu*f10[0])**2 - f10[1]**2 >= 0)
#                     # self.opti.subject_to(ca.dot(f10,c3) >= 0)
#                     # self.opti.subject_to(c3[1]==self.terrain.heightMap(c3[0]))
#                     # self.opti.subject_to(dc3==0)

#                     self.ceq.append((self.terrain.mu*f10[0])**2 - f10[1]**2 > 0)
#                     self.ceq.append(ca.dot(f10,c3) > 0)
#                     self.ceq.append(c3[1]==self.terrain.heightMap(c3[0]))
#                     self.ceq.append(dc3==0)

#     def setCollocationContraints(self):
#         for step in range(self.num_phases):
            
#             h = self.time_phases[str(step)]/self.knot_points_per_phase

#             for n in range(self.knot_points_per_phase-1):
#                 # if step > 0 and n==0:
#                 #     q_1   , q_2    = self.q   [str(step-1)][-1], self.q   [str(step)][n]
#                 #     qdot_1, qdot_2 = self.qdot[str(step-1)][-1], self.qdot[str(step)][n]
                    
#                 #     c3_1 , c3_2   = self.c3  [str(step-1)][-1], self.c3  [str(step)][n]
#                 #     dc3_1, dc3_2  = self.dc3 [str(step-1)][-1], self.dc3 [str(step)][n]
#                 #     ddc3_1,ddc3_2 = self.ddc3[str(step-1)][-1], self.ddc3[str(step)][n]
                    
#                 #     u_1  , u_2   = self.u  [str(step-1)][-1], self.u  [str(step)][n]
#                 #     f10_1, f10_2 = self.f10[str(step-1)][-1], self.f10[str(step)][n]

#                 #     m_1 = Hopper()
#                 #     m_1.setFullState(q=q_1, dq=qdot_1, 
#                 #                     c3=c3_1, dc3=dc3_1, ddc3=ddc3_1, 
#                 #                     u=u_1, f10=f10_1)
                    
#                 #     qddot_1 = m_1.dynamics['Leg']

#                 #     m_2 = Hopper()
#                 #     m_2.setFullState(q=q_2, dq=qdot_2, 
#                 #                     c3=c3_2, dc3=dc3_2, ddc3=ddc3_2,
#                 #                     u=u_2, f10=f10_2)
                    
#                 #     qddot_2 = m_2.dynamics['Leg']
                    
#                 #     self.ceq.append((h/2) * (qdot_2  + qdot_1)  == (q_2 - q_1))
#                 #     self.ceq.append((h/2) * (qddot_2 + qddot_1) == (qdot_2 - qdot_1))
#                 #     self.ceq.append((h/2) * (dc3_2  + dc3_1) == (c3_2 - dc3_1))
#                 #     self.ceq.append((h/2) * (ddc3_2 + ddc3_1) == (dc3_2 - dc3_1))

#                 q_1   , q_2    = self.q   [str(step)][n], self.q   [str(step)][n+1]
#                 qdot_1, qdot_2 = self.qdot[str(step)][n], self.qdot[str(step)][n+1]
                
#                 c3_1 , c3_2  = self.c3 [str(step)][n], self.c3 [str(step)][n+1]
#                 dc3_1, dc3_2 = self.dc3[str(step)][n], self.dc3[str(step)][n+1]
#                 # ddc3_1,ddc3_2 = self.ddc3[str(step)][n], self.ddc3[str(step)][n+1]
                
#                 u_1  , u_2   = self.u  [str(step)][n], self.u  [str(step)][n+1]
#                 f10_1, f10_2 = self.f10[str(step)][n], self.f10[str(step)][n+1]

#                 m_1 = Hopper()
#                 m_1.setFullState(q=q_1, dq=qdot_1, 
#                                  c3=c3_1, dc3=dc3_1, 
#                                  u=u_1, f10=f10_1)
                
#                 qddot_1 = m_1.dynamics['Leg']

#                 m_2 = Hopper()
#                 m_2.setFullState(q=q_2, dq=qdot_2, 
#                                  c3=c3_2, dc3=dc3_2, 
#                                  u=u_2, f10=f10_2)
                
#                 qddot_2 = m_2.dynamics['Leg']

                
#                 # self.opti.subject_to( (h/2) * (qdot_2  + qdot_1)  == (q_2 - q_1) )
#                 # self.opti.subject_to( (h/2) * (qddot_2 + qddot_1) == (qdot_2 - qdot_1) )
#                 # self.opti.bounded( 0,(h/2) * (dc3_2  + dc3_1) - (c3_2 - dc3_1), 0)
#                 # self.opti.bounded( 0, (h)*(self.model.gravity) - (dc3_2[1] - dc3_1[1]), 0)

#                 self.ceq.append((h/2) * (qdot_2  + qdot_1)  == (q_2 - q_1))
#                 self.ceq.append((h/2) * (qddot_2 + qddot_1) == (qdot_2 - qdot_1))
#                 self.ceq.append((h/2) * (dc3_2  + dc3_1) == (c3_2 - dc3_1))
#                 # self.ceq.append((h/2) * (ddc3_2 + ddc3_1) == (dc3_2 - dc3_1))

#     def setBounds(self):
#         # traj=0
#         for step in range(self.num_phases):
#             for knot_point in range(self.knot_points_per_phase):
#                 q    = self.q   [str(step)][knot_point]
#                 qdot = self.qdot[str(step)][knot_point]
                
#                 c3  = self.c3 [str(step)][knot_point]
#                 dc3 = self.dc3[str(step)][knot_point]
                
#                 u   = self.u  [str(step)][knot_point]
#                 f10 = self.f10[str(step)][knot_point]

#                 self.opti.bounded([-np.pi/2]*3, q,[np.pi/2]*3)
#                 self.opti.bounded([-1.5]*2, u,[1.5]*2)
                
#                 # traj+=(c3[1]**2)
                

#         # self.opti.minimize(traj)
