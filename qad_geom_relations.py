# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing relationships (intersections, tangency,
 perpendicularity, minimum distance) between basic geometric objects:
 line, arc, elliptical arc, circle, ellipse

                              -------------------
        begin                : 2019-02-28
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa ggggg
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *

import math
import sys

try:
   import numpy as np
except:
   raise Exception("Need to have numpy installed")

try:
   from scipy.optimize import fsolve, minimize
   NO_SCIPY = False
except:
   NO_SCIPY = True
   # raise Exception("Need to have scipy installed")

from .qad_line import QadLine
from .qad_circle import QadCircle
from .qad_arc import QadArc
from .qad_ellipse import QadEllipse
from .qad_ellipse_arc import QadEllipseArc

from . import qad_utils
from .qad_multi_geom import *


# ===============================================================================
# QadIntersections class
# represents a class that calculates intersections between basic objects: line, circle, arc, ellipse, arc of ellipse
# ===============================================================================
class QadIntersections():

   def __init__(self):
      pass

   # ===============================================================================
   # methods for infinite lines - start
   # ===============================================================================

   # ===============================================================================
   # twoInfinityLines
   # ===============================================================================
   @staticmethod
   def twoInfinityLines(line1, line2):
      """The function returns the intersection point between line1 and line2 considered infinite lines.
            The function returns None if the lines have no intersection.
      """
      return qad_utils.getIntersectionPointOn2InfinityLines(line1.pt1, line1.pt2, line2.pt1, line2.pt2)


   # ===============================================================================
   # infinityLineWithLine
   # ===============================================================================
   @staticmethod
   def infinityLineWithLine(infinityLine, line):
      """The function returns the point of intersection between an infinite line and a <line> segment.
            The function returns None if there is no intersection.
      """
      ptInt = QadIntersections.twoInfinityLines(infinityLine, line)
      if ptInt is None: return None
      if line.containsPt(ptInt) != True:
         return None
      return ptInt


   # ===============================================================================
   # infinityLineWithCircle
   # ===============================================================================
   @staticmethod
   def infinityLineWithCircle(infinityLine, circle):
      """The function returns the points of intersection between an infinite line and a circle."""
      # shift the geometries close to 0.0 to improve the accuracy of the calculations
      dx = circle.center.x()
      dy = circle.center.y()
      myInfinityLine = infinityLine.copy()
      myInfinityLine.move(-dx, -dy)
      myCircle = circle.copy()
      myCircle.move(-dx, -dy)

      if qad_utils.ptNear(myInfinityLine.pt1, myInfinityLine.pt2): return []

      x2_self = myCircle.center.x() * myCircle.center.x() # X of the center of the circle <myCircle> squared
      y2_self = myCircle.center.y() * myCircle.center.y() # Y of the center of the circle <myCircle> squared
      radius2_self = myCircle.radius * myCircle.radius # radius of circle <myCircle> squared

      diffX = myInfinityLine.pt2.x() - myInfinityLine.pt1.x()
      # if diffX is this close to zero
      if qad_utils.doubleNear(diffX, 0.0): # if myInfinityLine is a vertical line
         B = -2 * myCircle.center.y()
         C = x2_self + y2_self + (myInfinityLine.pt1.x() * myInfinityLine.pt1.x()) - (2* myInfinityLine.pt1.x() * myCircle.center.x()) - radius2_self
         D = (B * B) - (4 * C)
         # if D is so close to zero
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # you cannot take the square root of a negative number
            return []
         E = math.sqrt(D)

         y1 = (-B + E) / 2
         x1 = myInfinityLine.pt1.x()

         y2 = (-B - E) / 2
         x2 = myInfinityLine.pt1.x()
      else:
         m = (myInfinityLine.pt2.y() - myInfinityLine.pt1.y()) / diffX
         q = myInfinityLine.pt1.y() - (m * myInfinityLine.pt1.x())
         A = 1 + (m * m)
         B = (2 * m * q) - (2 * myCircle.center.x()) - (2 * m * myCircle.center.y())
         C = x2_self + (q * q) + y2_self - (2 * q * myCircle.center.y()) - radius2_self

         D = (B * B) - 4 * A * C
         # if D is so close to zero
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # you cannot take the square root of a negative number
            return []
         E = math.sqrt(D)

         x1 = (-B + E) / (2 * A)
         y1 = myInfinityLine.pt1.y() + m * x1 - m * myInfinityLine.pt1.x()

         x2 = (-B - E) / (2 * A)
         y2 = myInfinityLine.pt1.y() + m * x2 - m * myInfinityLine.pt1.x()

      # I translate the points to bring them back to their original position
      result = []
      result.append(QgsPointXY(x1 + dx, y1 + dy))
      if x1 != x2 or y1 != y2: # the points are not coincident
         result.append(QgsPointXY(x2 + dx, y2 + dy))

      return result


   # ===============================================================================
   # infinityLineWithArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithArc(infinityLine, arc):
      """The function returns the points of intersection between an infinite line and a circle."""
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.infinityLineWithCircle(infinityLine, circle)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # infinityLineWithEllipse
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipse(infinityLine, ellipse):
      """The function returns the points of intersection between an infinite line and an ellipse."""
      # http://www.ambrsoft.com/TrigoCalc/Circles2/Ellipse/EllipseLine.htm
      # the formula of the ellipse is:
      # (x - h)^2 / a^2 + (y - k)^2 / b^2 = 1
      # the formula of the line is:
      # y = mx + c
      # if h=0 and k=0 and c<>0 (horizontal ellipse with center at 0.0; line that does not pass through 0.0)

      # deltaForX = a * b * sqrt(a^2 * m^2 + b^2 - c^2)
      # deltaForY = a * b * m * sqrt(a^2 * m^2 + b^2 - c^2)
      # denom = a^2 * m^2 + b^2

      # x1 = (-a^2 * m * c + deltaForX) / denom
      # y1 = (b^2 * c + deltaForY) / denom
      # x2 = (-a^2 * m * c - deltaForX) / denom
      # y1 = (b^2 * c - deltaForY) / denom

      result = []
      # I translate and rotate the line to compare it with the ellipse with center at 0.0 and rotation = 0
      myP1 = ellipse.translateAndRotatePtForNormalEllipse(infinityLine.pt1, False)
      myP2 = ellipse.translateAndRotatePtForNormalEllipse(infinityLine.pt2, False)

      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semi-major axis
      b = a * ellipse.axisRatio # semi-minor axis

      # I call a m and b I call c in the equation of the line
      m, c = qad_utils.get_A_B_LineEquation(myP1.x(), myP1.y(), myP2.x(), myP2.y())

      dummy = a*a * m*m + b*b - c*c
      if dummy < 0: # you cannot take the square root of a negative number
         return result

      deltaForX = a * b * math.sqrt(dummy)
      deltaForY = a * b * m * math.sqrt(dummy)
      denom = a*a * m*m + b*b
      if denom == 0: return result

      x1 = (-(a*a) * m * c + deltaForX) / denom
      y1 = (b*b * c + deltaForY) / denom
      x2 = (-(a*a) * m * c - deltaForX) / denom
      y2 = (b*b * c - deltaForY) / denom

      # I translate and rotate the point to bring it back to the original position (with the center and rotation of the original ellipse)
      myP1.set(x1, y1)
      myP1 = ellipse.translateAndRotatePtForNormalEllipse(myP1, True)
      result.append(myP1)

      # I translate and rotate the point to bring it back to the original position (with the center and rotation of the original ellipse)
      myP2.set(x2, y2)
      myP2 = ellipse.translateAndRotatePtForNormalEllipse(myP2, True)
      result.append(myP2)

      return result


   # ===============================================================================
   # infinityLineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipseArc(infinityLine, ellipseArc):
      """The function returns the points of intersection between an infinite line and an arc of an ellipse."""
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.infinityLineWithEllipse(infinityLine, ellipse)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)

      return result


   # ===============================================================================
   # methods for infinite lines - end
   # segment methods - start
   # ===============================================================================


   # ===============================================================================
   # twoLines
   # ===============================================================================
   @staticmethod
   def twoLines(line1, line2):
      """The function returns the intersection point between 2 segments.
            The function returns None if the segments have no intersection.
      """
      intPt = QadIntersections.twoInfinityLines(line1, line2)
      if intPt is None: return None
      if line1.containsPt(intPt) == False or line2.containsPt(intPt) == False:
         return None
      return intPt


   # ===============================================================================
   # lineWithCircle
   # ===============================================================================
   @staticmethod
   def lineWithCircle(line, circle):
      """The function returns the intersection points between a segment and a circle."""
      result = []
      intPtList = QadIntersections.infinityLineWithCircle(line, circle)
      for intPt in intPtList:
         if line.containsPt(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # lineWithArc
   # ===============================================================================
   @staticmethod
   def lineWithArc(line, arc):
      """The function returns the intersection points between a segment and an arc."""
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.lineWithCircle(line, circle)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # lineWithEllipse
   # ===============================================================================
   @staticmethod
   def lineWithEllipse(line, ellipse):
      """The function returns the intersection points between a segment and an ellipse."""
      result = []
      intPtList = QadIntersections.infinityLineWithEllipse(line, ellipse)
      for intPt in intPtList:
         if line.containsPt(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # lineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def lineWithEllipseArc(line, ellipseArc):
      """The function returns the points of intersection between a segment and an arc of an ellipse."""
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.lineWithEllipse(line, ellipse)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # segment methods - end
   # methods for circles - start
   # ===============================================================================


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """The function returns the intersection points between 2 circles."""
      result = []
      # shift the geometries close to 0.0 to improve the accuracy of the calculations
      dx = circle1.center.x()
      dy = circle1.center.y()
      myCircle1 = circle1.copy()
      myCircle1.move(-dx, -dy)
      myCircle2 = circle2.copy()
      myCircle2.move(-dx, -dy)

      # if the points are so close that they are considered equal
      if qad_utils.ptNear(myCircle1.center, myCircle2.center): # same center
         return []
      distFromCenters = qad_utils.getDistance(myCircle1.center, myCircle2.center)
      distFromCirc = distFromCenters - myCircle1.radius - myCircle2.radius

      # if it is so close to zero that it is considered = 0
      if qad_utils.doubleNear(distFromCirc, 0):
         angle = qad_utils.getAngleBy2Pts(myCircle1.center, myCircle2.center)
         pt = qad_utils.getPolarPointByPtAngle(myCircle1.center, angle, myCircle1.radius)
         # I move the point to bring it back to its original position
         pt.set(pt.x() + dx, pt.y() + dy)
         result.append(pt)
         return result

      if distFromCirc > 0: # i cerchi sono troppo distanti
         return []

      x2_myCircle1 = myCircle1.center.x() * myCircle1.center.x() # X of the center of the circle <myCircle1> squared
      x2_circle = myCircle2.center.x() * myCircle2.center.x() # Y of the center of the circle <myCircle2> squared
      radius2_myCircle1 = myCircle1.radius * myCircle1.radius # radius of circle <myCircle1> squared
      radius2_circle = myCircle2.radius * myCircle2.radius # radius of circle <myCircle2> squared

      if qad_utils.doubleNear(myCircle1.center.y(), myCircle2.center.y()):
         x1 = x2_circle - x2_myCircle1 + radius2_myCircle1 - radius2_circle
         x1 = x1 / (2 * (myCircle2.center.x() - myCircle1.center.x()))
         x2 = x1
         D = radius2_myCircle1 - ((x1 - myCircle1.center.x()) * (x1 - myCircle1.center.x()))
         # if D is so close to zero
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # you cannot take the square root of a negative number
            return []
         E = math.sqrt(D)

         y1 = myCircle1.center.y() + E
         y2 = myCircle1.center.y() - E
      else:
         y2_myCircle1 = myCircle1.center.y() * myCircle1.center.y() # Y of the center of the circle <myCircle1> squared
         y2_circle = myCircle2.center.y() * myCircle2.center.y() # Y of the center of the circle <myCircle2> squared

         a = (myCircle1.center.x() - myCircle2.center.x()) / (myCircle2.center.y() - myCircle1.center.y())
         b = x2_circle - x2_myCircle1 + y2_circle - y2_myCircle1 + radius2_myCircle1 - radius2_circle
         b = b / (2 * (myCircle2.center.y() - myCircle1.center.y()))

         A = 1 + (a * a)
         B = (2 * a * b) - (2 * myCircle1.center.x()) - (2 * a * myCircle1.center.y())
         C = (b * b) - (2 * myCircle1.center.y() * b) + x2_myCircle1 + y2_myCircle1 - radius2_myCircle1
         D = (B * B) - (4 * A * C)
         # if D is so close to zero
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # you cannot take the square root of a negative number
            return []
         E = math.sqrt(D)

         x1 = (-B + E) / (2 * A)
         y1 = a * x1 + b

         x2 = (-B - E) / (2 * A)
         y2 = a * x2 + b

      # I translate the points to bring them back to their original position
      result.append(QgsPointXY(x1 + dx, y1 + dy))
      if x1 != x2 or y1 != y2: # the points are not coincident
         result.append(QgsPointXY(x2 + dx, y2 + dy))

      return result


   # ===============================================================================
   # circleWithArc
   # ===============================================================================
   @staticmethod
   def circleWithArc(circle, arc):
      """The function returns the points of intersection between a circle and an arc."""
      result = []
      circle1 = QadCircle()
      circle1.set(arc.center, arc.radius)
      intPtList = QadIntersections.twoCircles(circle, circle1)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # generate_initial_guesses
   # Function to generate initial guesses for circle-ellipse intersection calculations (chatgpt)
   # ===============================================================================
   def generate_initial_guesses(h, k, a, b, theta, num_points=20):
      t = np.linspace(0, 2 * np.pi, num_points)
      x_ellipse = a * np.cos(t)
      y_ellipse = b * np.sin(t)

      initial_guesses = []
      for x_e, y_e in zip(x_ellipse, y_ellipse):
          x_rotated = h + (x_e * np.cos(theta) - y_e * np.sin(theta))
          y_rotated = k + (x_e * np.sin(theta) + y_e * np.cos(theta))
          initial_guesses.append((x_rotated, y_rotated))

      return initial_guesses


   # ===============================================================================
   # rotate
   # Coordinate transformation function for circle-ellipse intersection calculations (chatgpt)
   # ===============================================================================
   def rotate(x, y, theta):
      x_prime = x * np.cos(theta) + y * np.sin(theta)
      y_prime = -x * np.sin(theta) + y * np.cos(theta)
      return x_prime, y_prime


# ============================================================================
   # getEquationForIntCicleEllipse
   # Defines a system of nonlinear equations for circle-ellipse intersection calculations (chatgpt)
   # x and y: center
   # a and b: the semi-axes of the ellipse
   # theta: the rotation angle of the ellipse
   # h and k: the translations of the ellipse with respect to the origin.
   # ============================================================================
   @staticmethod
   def getEquationForIntCicleEllipse(xy, circle, ellipse):
      x, y = xy

      circle_eq = (x - circle.center.x())**2 + (y - circle.center.y())**2 - circle.radius**2

      return [circle_eq, QadIntersections.getEquationForEllipse(xy, ellipse)]


   # ===============================================================================
   # circleWithEllipse
   # ===============================================================================
   @staticmethod
   def circleWithEllipse(circle, ellipse):
      """The function returns the intersection points between a circle and an ellipse."""
      if NO_SCIPY == True: return []

      # Calculate the length of the major axis (a)
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt)
      # Calculate the length of the minor axis (b)
      b = a * ellipse.axisRatio
      # theta: the rotation angle of the ellipse.
      theta = ellipse.getRotation()
      # h and k: the translations of the ellipse with respect to the origin, center coordinates
      h = ellipse.center.x()
      k = ellipse.center.y()

      args = (circle, ellipse)

      # Generiamo i guess iniziali
      initial_guesses = QadIntersections.generate_initial_guesses(h, k, a, b, theta)

      # Risoluzione del sistema di equazioni
      intersections = []
      for guess in initial_guesses:
          sol = fsolve(QadIntersections.getEquationForIntCicleEllipse, guess, args)
          if not any(np.isclose(sol, x).all() for x in intersections):
              intersections.append(sol)

      result = []
      for intersection in intersections:
         result.append(QgsPointXY(intersection[0], intersection[1]))

      return result

#       # http://it.scienza.matematica.narkive.com/cTzzSW1r/intersection-tra-ellisse-e-circonformazione
#       result = []
#
#       # I translate and rotate the center of the circle to compare it with the ellipse with center at 0.0 and rotation = 0
#       myCircle = QadCircle(circle)
#       myCircle.center = ellipse.translateAndRotatePtForNormalEllipse(circle.center, False)
#
#       a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semi-major axis
#       b = a * ellipse.axisRatio # semi-minor axis
#
#       a2 = a * a # a al quadrato
#       a4 = a2 * a2 # a alla quarta
#       b2 = b * b # b al quadrato
#       c2 = (a / b) * (a / b)
#       c4 = c2 * c2
#       r = myCircle.radius
#       r2 = r * r
#       xc = myCircle.center.x() # x of the center of the circle
#       xc2 = xc * xc # x squared circle
#       yc = myCircle.center.y() # y of the center of the circle
#       yc2 = yc * yc # y squared circle
#       a2_b2 = a2 - b2
#
# # [a^4+(p^2+q^2-r^2)^2-2a^2(p^2-q^2+r^2] +
# # y [4q(r^2-a^2-p^2-q^2)] +
# #       y^2 [2a^2-2a^2c^2+2p^2+2c^2p^2+6q^2-2c^2q^2-2r^2+2c^2r^2] +
# #       y^3 [4c^2q-4q]+
# #       y^4 [1-2c^2+c^4] = 0
#
#       z0 = a4 + (xc2 + yc2 - r2) * (xc2 + yc2 - r2) - (2 * a2) * (xc2 - yc2 + r2)
#       z1 = (4 * yc2) * (r2 - a2 - xc2 - yc2)
#       z2 = (2 * a2) - (2 * a2 * c2) + 2 *xc2 + (2 * c2 * xc2) + (6 * yc2) - (2 *c2 * yc2) - (2 * r2) + (2 * c2 * r2)
#       z3 = (4 * c2 * yc) - (4 * yc)
#       z4 = 1 - (2 * c2) + c4
#
#       y_result = np.roots([z4, z3, z2, z1, z0])
#       for y in y_result:
#          y = float(y)
#          n = (1.0 - y * y / b2) * a2 # given the Y calculate the
#          if qad_utils.doubleNear(n, 0): n = 0 # for calculation precision problems (e.g. if x = 10 , n = -1.11022302463e-14 !)
#          if n >= 0:
#             x = math.sqrt(n)
#             p = QgsPointXY(x, y)
#             # check if the point is OK
#             dist = qad_utils.getDistance(p, myCircle.center)
#             # if the distance coincides with the radius of the circle
#             if qad_utils.doubleNear(dist, myCircle.radius, 1.e-1): # I know it sucks but the approximation of the calculations...
#                # I translate and rotate the point to bring it back to the original position (with the center and rotation of the original ellipse)
#                p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
#                qad_utils.appendUniquePointToList(result, p)
#
#             # verifico l'altra coordinata x
#             p = QgsPointXY(-x, y)
#             # check if the point is OK
#             dist = qad_utils.getDistance(p, myCircle.center)
#             # if the distance coincides with the radius of the circle
#             if qad_utils.doubleNear(dist, myCircle.radius, 1.e-1): # I know it sucks but the approximation of the calculations...
#                # I translate and rotate the point to bring it back to the original position (with the center and rotation of the original ellipse)
#                p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
#                qad_utils.appendUniquePointToList(result, p)
#
#       return result


   # ===============================================================================
   # circleWithEllipseArc
   # ===============================================================================
   @staticmethod
   def circleWithEllipseArc(circle, ellipseArc):
      """The function returns the points of intersection between a circle and an arc of an ellipse."""
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.circleWithEllipse(circle, ellipse)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # methods for circles - end
   # methods for arcs - start
   # ===============================================================================


   # ===============================================================================
   # twoArcs
   # ===============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """The function returns the intersection points between 2 arcs."""
      result = []
      circle = QadCircle()
      circle.set(arc1.center, arc1.radius)
      intPtList = QadIntersections.circleWithArc(circle, arc2)
      for intPt in intPtList:
         if arc1.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # arcWithEllipseArc
   # ===============================================================================
   @staticmethod
   def arcWithEllipseArc(arc, ellipseArc):
      """The function returns the points of intersection between an arc and an arc of an ellipse."""
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.circleWithEllipseArc(circle, ellipseArc)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # methods for arcs - end
   # methods for ellipses - start
   # ===============================================================================


   # ============================================================================
   # getEquationForEllipse
   # Defines a function that represents a rotated and translated ellipse
   # x and y: center
   # a and b: the semi-axes of the ellipse
   # theta: the rotation angle of the ellipse
   # h and k: the translations of the ellipse with respect to the origin.
   # ============================================================================
   @staticmethod
   def getEquationForEllipse(xy, ellipse):
      x, y = xy
      # Calculate the length of the major axis (a)
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt)
      # Calculate the length of the minor axis (b)
      b = a * ellipse.axisRatio
      # theta: the rotation angle of the ellipse.
      theta = ellipse.getRotation()
      # h and k: the translations of the ellipse with respect to the origin, center coordinates
      h = ellipse.center.x()
      k = ellipse.center.y()

      cos_t = np.cos(theta)
      sin_t = np.sin(theta)
      term1 = ((x - h) * cos_t + (y - k) * sin_t) ** 2 / a ** 2
      term2 = ((x - h) * sin_t - (y - k) * cos_t) ** 2 / b ** 2
      return term1 + term2 - 1


   @staticmethod
   def sistema(xy, ellipse1, ellipse2):
      return [QadIntersections.getEquationForEllipse(xy, ellipse1), QadIntersections.getEquationForEllipse(xy, ellipse2)]


   # ===============================================================================
   # twoEllipses
   # ===============================================================================
   @staticmethod
   def twoEllipses(ellipse1, ellipse2):
      """The function returns the points of intersection between 2 ellipses (chatGPT)"""
      if NO_SCIPY == True: return []

      # test
#       l1 = QadLine()
#       l1.set(QgsPointXY(1, 2), QgsPointXY(3, 4))
#
#       center = QgsPointXY(0, 0)
#       a = 2
#       b = 1
#       axisRatio = b / a
#       theta = math.pi / 4
#       ellipse1 = QadEllipse()
#       majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, theta, a)
#       ellipse1.set(center, majorAxisFinalPt, axisRatio)
#       QadMinDistance.fromLineToEllipse(l1, ellipse1)

#
#
#       center = QgsPointXY(-1, -2)
#       a = 4
#       b = 2
#       axisRatio = b / a
#       theta = math.pi / 4
#       ellipse2 = QadEllipse()
#       majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, theta, a)
#       ellipse2.set(center, majorAxisFinalPt, axisRatio)


      args = (ellipse1, ellipse2)
      # Generates initial estimates in a grid around the centers of the ellipses
      x_vals = np.linspace(-10, 10, 10)
      y_vals = np.linspace(-10, 10, 10)
      stima_iniziali = np.array(np.meshgrid(x_vals, y_vals)).T.reshape(-1, 2)

      # Find intersections using fsolve from several initial estimates
      soluzioni = []
      for stima in stima_iniziali:
          soluzione = fsolve(QadIntersections.sistema, stima, args)
          if QadIntersections.sistema(soluzione, ellipse1, ellipse2)[0] < 1e-6 and QadIntersections.sistema(soluzione, ellipse1, ellipse2)[1] < 1e-6:
              soluzioni.append(soluzione)

      # Rimuovi soluzioni duplicate (vicine)
      tolleranza = 1e-4
      soluzioni_uniche = []
      for sol in soluzioni:
          if not any(np.linalg.norm(sol - s) < tolleranza for s in soluzioni_uniche):
              soluzioni_uniche.append(sol)

      result = []
      for sol in soluzioni_uniche:
         result.append(QgsPointXY(sol[0], sol[1]))

      return result


   # ===============================================================================
   # ellipseWithArc
   # ===============================================================================
   @staticmethod
   def ellipseWithArc(ellipse, arc):
      """The function returns the points of intersection between an ellipse and an arc."""
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.circleWithEllipse(circle, ellipse)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # ellipseWithEllipseArc
   # ===============================================================================
   @staticmethod
   def ellipseWithEllipseArc(ellipse, ellipseArc):
      """The function returns the points of intersection between an ellipse and an arc of an ellipse."""
      result = []
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.twoEllipses(ellipse, ellipse1)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # methods for ellipses - end
   # methods for ellipse arcs - start
   # ===============================================================================


   # ===============================================================================
   # twoEllipseArcs
   # ===============================================================================
   @staticmethod
   def twoEllipseArcs(EllipseArc1, EllipseArc2):
      """The function returns the intersection points between 2 ellipse arcs."""
      result = []
      ellipse1 = QadEllipse()
      ellipse1.set(EllipseArc1.center, EllipseArc1.majorAxisFinalPt, EllipseArc1.axisRatio)
      intPtList = QadIntersections.ellipseWithEllipseArc(ellipse1, EllipseArc2)
      for intPt in intPtList:
         if EllipseArc1.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # methods for ellipse arcs - end
   # methods for basic geometric objects - start
   # ===============================================================================


   # ============================================================================
   # twoBasicGeomObjects
   # ============================================================================
   @staticmethod
   def twoBasicGeomObjects(object1, object2):
      """the function calculates the intersection points between 2 basic geometric objects:
            line, arc, ellipse arc, circle, ellipse.
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            result = QadIntersections.twoLines(object1, object2)
            return [result] if result is not None else []
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.lineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadIntersections.lineWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.lineWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.lineWithEllipseArc(object1, object2)

      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadIntersections.circleWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.circleWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.circleWithEllipseArc(object1, object2)

      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadIntersections.twoArcs(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.arcWithEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadIntersections.ellipseWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.twoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.ellipseWithEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithEllipseArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadIntersections.arcWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.twoEllipseArcs(object1, object2)

      return []


   # ============================================================================
   # twoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def twoBasicGeomObjectExtensions(object1, object2):
      """the function calculates the intersection points between the extensions of 2 basic geometric objects:
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            result = QadIntersections.twoInfinityLines(object1, object2)
            return [result] if result is not None else ()
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.infinityLineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.infinityLineWithCircle(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.infinityLineWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.infinityLineWithEllipse(object1, ellipse)

      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.twoCircles(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.circleWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.circleWithEllipse(object1, ellipse)

      elif object1.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object1.center, object1.radius)
         return QadIntersections.twoBasicGeomObjectExtensions(circle, object2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.circleWithEllipse(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.twoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.twoEllipses(object1, ellipse)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         return QadIntersections.twoBasicGeomObjectExtensions(ellipse, object2)

      return []


   # ============================================================================
   # basicGeomObjectWithBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def basicGeomObjectWithBasicGeomObjectExtensions(object1, object2):
      """the function calculates the intersection points between a basic geometric object (object1) and
            the extensions of basic geometric objects (object2):
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            result = QadIntersections.infinityLineWithLine(object2, object1)
            return [result] if result is not None else ()
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.lineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.lineWithCircle(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.lineWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.lineWithEllipse(object1, ellipse)

      elif object1.whatIs() == "CIRCLE":
         return QadIntersections.twoBasicGeomObjectExtensions(object1, object2)

      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithArc(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.circleWithArc(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.ellipseWithArc(ellipse, object1)

      elif object1.whatIs() == "ELLIPSE":
         return QadIntersections.twoBasicGeomObjectExtensions(object1, object2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithEllipseArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.circleWithEllipseArc(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.ellipseWithEllipseArc(ellipse, object1)

      return []


   # ============================================================================
   # twoGeomObjects
   # ============================================================================
   @staticmethod
   def twoGeomObjects(object1, object2, object2GeomBoundingBoxCache = None):
      """the function calculates the intersection points between 2 geometric objects"""
      if object1 is None or object2 is None:
         return []

      geomType1 = object1.whatIs()
      result = []

      if object2GeomBoundingBoxCache is None:
         object2GeomBoundingBoxCache = QadGeomBoundingBoxCache(object2)

      if geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            pt = object1.getPointAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(pt, object2, object2GeomBoundingBoxCache))

      elif geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(linearObj, object2, object2GeomBoundingBoxCache))

      elif geomType1 == "POLYLINE":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(linearObj, object2, object2GeomBoundingBoxCache))

      elif geomType1 == "POLYGON":
         for geomAt in range(0, object1.qty()):
            closedObj = object1.getClosedObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(closedObj, object2, object2GeomBoundingBoxCache))

      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            polygon = object1.getPolygonAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(polygon, object2, object2GeomBoundingBoxCache))

      # object 1 is a basic geometry
      elif object1.whatIs() == "POINT" or object1.whatIs() == "LINE" or object1.whatIs() == "CIRCLE" or \
           object1.whatIs() == "ARC" or object1.whatIs() == "ELLIPSE" or object1.whatIs() == "ELLIPSE_ARC":
         geomType2 = object2.whatIs()

         if object2GeomBoundingBoxCache is not None and object2GeomBoundingBoxCache.cacheLayer is not None:
            # I only read the parts that intersect with the bounding box of object1
            boundingBox = object1.getBoundingBox()
            geomSubgeomPartAtList = object2GeomBoundingBoxCache.getIntersectionWithBoundingBox(boundingBox)
            for geomSubgeomPartAt in geomSubgeomPartAtList:
               part = getQadGeomPartAt(object2, geomSubgeomPartAt[0], geomSubgeomPartAt[1], geomSubgeomPartAt[2])
               result.extend(QadIntersections.twoBasicGeomObjects(object1, part))

         elif geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoBasicGeomObjects(object1, object2.getPointAt(geomAt)))

         elif geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getLinearObjectAt(geomAt)))

         elif geomType2 == "POLYLINE":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getLinearObjectAt(geomAt)))

         elif geomType2 == "POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getClosedObjectAt(geomAt)))

         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getPolygonAt(geomAt)))

         # object 1 is a basic geometry
         elif object2.whatIs() == "POINT" or object2.whatIs() == "LINE" or object2.whatIs() == "CIRCLE" or \
              object2.whatIs() == "ARC" or object2.whatIs() == "ELLIPSE" or object2.whatIs() == "ELLIPSE_ARC":
            result = QadIntersections.twoBasicGeomObjects(object1, object2)

      return result


   # ============================================================================
   # twoGeomObjectsExtensions
   # ============================================================================
   @staticmethod
   def twoGeomObjectsExtensions(object1, object2):
      """the function calculates the intersection points between the extensions of 2 geometric objects:
            line (becomes infinite line), arc (becomes circle), arc of ellipse (becomes ellipse).
      """
      if object1 is None or object2 is None:
         return []

      geomType1 = object1.whatIs()
      result = []

      if geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            pt = object1.getPointAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(pt, object2))

      elif geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(linearObj, object2))

      elif geomType1 == "POLYLINE":
         if object1.qty() > 0: # first part of the polyline
            linearObj = object1.getLinearObjectAt(0)
            pts = QadIntersections.twoGeomObjectsExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               reversedLine = linearObj.copy()
               appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
            else:
               result.extend(pts)

         for geomAt in range(1, object1.qty()-1):
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1.getLinearObjectAt(geomAt), object2))

         if object1.qty() > 1: # last part of the polyline
            linearObj = object1.getLinearObjectAt(-1)
            pts = QadIntersections.twoGeomObjectsExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
            else:
               result.extend(pts)

      elif geomType1 == "POLYGON":
         for subGeomAt in range(0, object1.qty()):
            closedObj = object1.getClosedObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(closedObj, object2))

      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            polygon = object1.getPolygonAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(polygon, object2))

      # object 1 is a basic geometry
      elif object1.whatIs() == "POINT" or object1.whatIs() == "LINE" or object1.whatIs() == "CIRCLE" or \
           object1.whatIs() == "ARC" or object1.whatIs() == "ELLIPSE" or object1.whatIs() == "ELLIPSE_ARC":
         geomType2 = object2.whatIs()

         if geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoBasicGeomObjectExtensions(object1, object2.getPointAt(geomAt)))

         elif geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjectsExtensions(object1, object2.getLinearObjectAt(geomAt)))

         elif geomType2 == "POLYLINE":
            if object2.qty() > 0: # first part of the polyline
               linearObj = object2.getLinearObjectAt(0)
               pts = QadIntersections.twoGeomObjectsExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  reversedLine = linearObj.copy()
                  appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
               else:
                  result.extend(pts)

            for geomAt in range(1, object2.qty()-1):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object2.getLinearObjectAt(geomAt), object1))

            if object2.qty() > 1: # last part of the polyline
               linearObj = object2.getLinearObjectAt(-1)
               pts = QadIntersections.twoGeomObjectsExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
               else:
                  result.extend(pts)

         elif geomType2 == "POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjectsExtensions(object1, object2.getClosedObjectAt(geomAt)))

         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjectsExtensions(object1, object2.getPolygonAt(geomAt)))

         # object 2 is a basic geometry
         elif object2.whatIs() == "POINT" or object2.whatIs() == "LINE" or object2.whatIs() == "CIRCLE" or \
              object2.whatIs() == "ARC" or object2.whatIs() == "ELLIPSE" or object2.whatIs() == "ELLIPSE_ARC":
            result = QadIntersections.twoBasicGeomObjectExtensions(object1, object2)

      return result


   # ============================================================================
   # geomObjectWithGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def geomObjectWithGeomObjectExtensions(object1, object2):
      """the function calculates the intersection points between a geometric object (object1) and
            the extensions of a geometric object (object2)
      """
      if object1 is None or object2 is None:
         return []

      geomType1 = object1.whatIs()
      result = []

      if geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            pt = object1.getPointAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(pt, object2))

      elif geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(linearObj, object2))

      elif geomType1 == "POLYLINE":
         if object1.qty() > 0: # first part of the polyline
            linearObj = object1.getLinearObjectAt(0)
            pts = QadIntersections.geomObjectWithGeomObjectExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               reversedLine = linearObj.copy()
               appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
            else:
               result.extend(pts)

         for geomAt in range(1, object1.qty()-1):
            result.extend(QadIntersections.twoGeomObjects(object1.getLinearObjectAt(geomAt), object2))

         if object1.qty() > 1: # last part of the polyline
            linearObj = object1.getLinearObjectAt(-1)
            pts = QadIntersections.geomObjectWithGeomObjectExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
            else:
               result.extend(pts)

      elif geomType1 == "POLYGON":
         for subGeomAt in range(0, object1.qty()):
            closedObj = object1.getClosedObjectAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(closedObj, object2))

      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            polygon = object1.getPolygonAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(polygon, object2))

      # object 1 is a basic geometry
      elif object1.whatIs() == "POINT" or object1.whatIs() == "LINE" or object1.whatIs() == "CIRCLE" or \
           object1.whatIs() == "ARC" or object1.whatIs() == "ELLIPSE" or object1.whatIs() == "ELLIPSE_ARC":
         geomType2 = object2.whatIs()

         if geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getPointAt(geomAt)))

         elif geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getLinearObjectAt(geomAt)))

         elif geomType2 == "POLYLINE":
            if object2.qty() > 0: # first part of the polyline
               linearObj = object2.getLinearObjectAt(0)
               pts = QadIntersections.geomObjectWithGeomObjectExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  reversedLine = linearObj.copy()
                  appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
               else:
                  result.extend(pts)

            for geomAt in range(1, object2.qty()-1):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getLinearObjectAt(geomAt)))

            if object2.qty() > 1: # last part of the polyline
               linearObj = object2.getLinearObjectAt(-1)
               pts = QadIntersections.geomObjectWithGeomObjectExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
               else:
                  result.extend(pts)

         elif geomType2 == "POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getClosedObjectAt(geomAt)))

         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getPolygonAt(geomAt)))

         # object 2 is a basic geometry
         elif object2.whatIs() == "POINT" or object2.whatIs() == "LINE" or object2.whatIs() == "CIRCLE" or \
              object2.whatIs() == "ARC" or object2.whatIs() == "ELLIPSE" or object2.whatIs() == "ELLIPSE_ARC":
            result = QadIntersections.basicGeomObjectWithBasicGeomObjectExtensions(object1, object2)

      return result


   # ===============================================================================
   # getOrderedPolylineIntersectionPtsWithBasicGeom
   # ===============================================================================
   @staticmethod
   def getOrderedPolylineIntersectionPtsWithBasicGeom(polyline, linearObject, orderByStartPtOfLinearObject = False):
      """The function returns several lists:
            - the first is a list of intersection points between the <linearObject> part and the polyline.
              The list is ordered by distance from the starting point of <linearObject> if <orderByStartPtOfLinearObject> = True
              otherwise it is ordered by distance from the starting point of the polyline
            - the second is a list that contains, respectively for each intersection point,
              the part number (0-based) of the polyline where that point is located.
            - the third is a list that contains, respectively for each intersection point,
              the distance from the starting point of <linearObject> if <orderByStartPtOfLinearObject> = True or
              from the starting point of the polyline if <orderByStartPtOfLinearObject> = False
      """
      gType = linearObject.whatIs()
      if polyline.whatIs() != "POLYLINE" or \
         (gType != "LINE" and gType != "ARC" and gType != "ELLIPSE_ARC"):
         return [], [], []

      intPtSortedList = [] # list of ((point, distance from start of linearObject)...)
      partNumber = -1
      if orderByStartPtOfLinearObject == False:
         distFromStartPrevParts = 0

      # for each part of the list
      i = 0
      while i < polyline.qty():
         linearObject2 = polyline.getLinearObjectAt(i)
         partNumber = partNumber + 1
         partialIntPtList = QadIntersections.twoBasicGeomObjects(linearObject, linearObject2)

         for partialIntPt in partialIntPtList:
            # I exclude points that are already in intPtSortedList
            found = False
            for intPt in intPtSortedList:
               if qad_utils.ptNear(intPt[0], partialIntPt):
                  found = True
                  break

            if found == False:
               if orderByStartPtOfLinearObject:
                  # insert the point ordered by distance from the start of linearObject
                  distFromStart = linearObject.getDistanceFromStart(partialIntPt)
               else:
                  distFromStart = distFromStartPrevParts + linearObject2.getDistanceFromStart(partialIntPt)

               insertAt = 0
               for intPt in intPtSortedList:
                  if intPt[1] < distFromStart:
                     insertAt = insertAt + 1
                  else:
                     break
               intPtSortedList.insert(insertAt, [partialIntPt, distFromStart, partNumber])

         if orderByStartPtOfLinearObject == False:
            distFromStartPrevParts = distFromStartPrevParts + linearObject2.length()
         i = i + 1

      resultIntPt = []
      resultPartNumber = []
      resultDistanceFromStart = []
      for intPt in intPtSortedList:
         resultIntPt.append(intPt[0])
         resultPartNumber.append(intPt[2])
         resultDistanceFromStart.append(intPt[1])

      return resultIntPt, resultPartNumber, resultDistanceFromStart


   # ===============================================================================
   # getOrderedPolylineIntersectionPtsWithPolyline
   # ===============================================================================
   @staticmethod
   def getOrderedPolylineIntersectionPtsWithPolyline(polyline1, polyline2):
      """the function returns several lists:
            - the first is a list of intersection points between the 2 polylines
            sorted by distance from the starting point of <polyline2> .
            - the second is a list that contains, respectively for each intersection point,
            the number of the part of the <polyline2> (0-based) where that point is located.
            - the third is a list that contains, respectively for each intersection point,
            the distance from the starting point of the polyline2.
      """
      if polyline1.whatIs() != "POLYLINE" or polyline2.whatIs() != "POLYLINE":
         return [], [], []

      resultIntPt = []
      resultPartNumber = []
      resultDistanceFromStart = []

      # for each part of the list
      i = 0
      while i < polyline1.qty():
         linearObject1 = polyline1.getLinearObjectAt(i)
         # list of intersection points ordered by distance from the starting point of <linearObject1>
         partialResult = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(polyline2, linearObject1, orderByStartPtOfLinearObject = True)
         resultIntPt.extend(partialResult[0])
         resultPartNumber.extend(partialResult[2])
         resultDistanceFromStart.extend(partialResult[1])
         i = i + 1

      return resultIntPt, resultPartNumber, resultDistanceFromStart


# ===============================================================================
# QadPerpendicularity class
# represents a class that calculates perpendicularity between basic objects: point, line, arc, ellipse arc, circle, ellipse
# ===============================================================================
class QadPerpendicularity():

   def __init__(self):
      pass


   # ===============================================================================
   # methods for infinite lines - start
   # ===============================================================================

   # ===============================================================================
   # fromPointToInfinityLine
   # ===============================================================================
   @staticmethod
   def fromPointToInfinityLine(pt, line):
      """the function returns the perpendicular projection of point on an infinite line"""
      return qad_utils.getPerpendicularPointOnInfinityLine(line.pt1, line.pt2, pt)


   # ===============================================================================
   # methods for infinite lines - end
   # segment methods - start
   # ===============================================================================


   # ===============================================================================
   # fromPointToLine
   # ===============================================================================
   @staticmethod
   def fromPointToLine(pt, line):
      """the function returns the perpendicular projection of a point on a segment"""
      perpPt = QadPerpendicularity.fromPointToInfinityLine(pt, line)
      if line.containsPt(perpPt):
         return perpPt
      return None


   # ===============================================================================
   # getInfinityLinePerpOnMiddle
   # ===============================================================================
   @staticmethod
   def getInfinityLinePerpOnMiddleLine(line):
      """the function finds a line perpendicular to and passing through the midpoint of the line."""
      ptMiddle = line.getMiddlePt()
      dist = qad_utils.getDistance(line.pt1, ptMiddle)
      if dist == 0:
         return None
      angle = qad_utils.getAngleBy2Pts(line.pt1, line.pt2) + math.pi / 2
      pt2Middle = qad_utils.getPolarPointByPtAngle(ptMiddle, angle, dist)
      line = QadLine()
      line.set(ptMiddle, pt2Middle)
      return line


   # ===============================================================================
   # segment methods - end
   # methods for circles - start
   # ===============================================================================


   # ===============================================================================
   # fromPointToCircle
   # ===============================================================================
   @staticmethod
   def fromPointToCircle(pt, circle):
      """the function returns the perpendicular projections of points on a circle"""
      angle = qad_utils.getAngleBy2Pts(circle.center, pt)
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(circle.center, angle + math.pi, circle.radius)
      return [pt1, pt2]


   # ===============================================================================
   # methods for circles - end
   # methods for arcs - start
   # ===============================================================================


   # ============================================================================
   # fromPointToArc
   # ============================================================================
   @staticmethod
   def fromPointToArc(pt, arc):
      """the function returns the perpendicular projection of a point on an arc"""
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      perpPtList = QadPerpendicularity.fromPointToCircle(pt, circle)
      for perpPt in perpPtList:
         if arc.isPtOnArcOnlyByAngle(perpPt):
            result.append(perpPt)
      return result


   # ===============================================================================
   # methods for arcs - end
   # methods for ellipses - start
   # ===============================================================================


   # ============================================================================
   # fromPointToEllipse
   # ============================================================================
   @staticmethod
   def fromPointToEllipse(pt, ellipse):
      """the function returns the perpendicular projection of a point onto an ellipse (up to 4 points)"""
      # https://www.mathpages.com/home/kmath505/kmath505.htm (for points outside the ellipse)
      # https://math.stackexchange.com/questions/609351/number-of-normals-from-a-point-to-an-ellipse (for points inside the ellipse)
      result = []

      # returns -1 if the point is internal, 0 if it is on the ellipse, 1 if it is external
      whereIsPt = ellipse.whereIsPt(pt)
      if whereIsPt == 0: # pt is on the ellipse
         result.append(QgsPointXY(pt.x(), pt.y()))
         return result

      # I translate and rotate the point to compare it with the ellipse with center at 0.0 and with rotation = 0
      myPoint = ellipse.translateAndRotatePtForNormalEllipse(pt, False)

      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semi-major axis
      b = a * ellipse.axisRatio # semi-minor axis
      e = QadEllipse(ellipse)
      e.center.set(0.0, 0.0)
      e.majorAxisFinalPt.set(a, 0.0)

      a2 = a * a # a al quadrato
      b2 = b * b # b al quadrato
      xp = myPoint.x() # x of the point
      xp2 = xp * xp # xp al quadrato
      yp = myPoint.y()
      yp2 = yp * yp # yp al quadrato
      a2_b2 = a2 - b2

      c4 = a2_b2 * a2_b2
      c3 = -2 * a2 * xp * a2_b2
      c2 = a2 * (a2 * xp2 + b2 * yp2 - (a2_b2 * a2_b2))
      c1 = 2 * a2 * a2 * xp * a2_b2
      c0 = -1 * (a2 * a2 * a2) * xp2

      x_result = np.roots([c4, c3, c2, c1, c0])
      for x in x_result:
         n = (1.0 - x * x / a2) * b2 # given X calculate Y
         if qad_utils.doubleNear(n, 0): n = 0 # for calculation precision problems (e.g. if x = 10, n = -1.11022302463e-14!)
         if n >= 0:
            y = math.sqrt(n)
            p = QgsPointXY(x, y)
            # check if the point is OK
            # calculate the tangent on that point
            t = e.getTanDirectionOnPt(p)
            # if it is perpendicular to the segment that joins the point found with the one provided (myPoint)
            angSegment = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(p, myPoint) + math.pi / 2)
            if qad_utils.doubleNear(t, angSegment) or qad_utils.doubleNear(qad_utils.normalizeAngle(t + math.pi), angSegment):
               # I translate and rotate the point to bring it back to the original position (with the center and rotation of the original ellipse)
               p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
               qad_utils.appendUniquePointToList(result, p)

            # verifico l'altra coordinata y
            p = QgsPointXY(x, -y)
            # check if the point is OK
            # calculate the tangent on that point
            t = e.getTanDirectionOnPt(p)
            # if it is perpendicular to the segment that joins the point found with the one provided (myPoint)
            angSegment = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(p, myPoint) + math.pi / 2)
            if qad_utils.doubleNear(t, angSegment) or qad_utils.doubleNear(qad_utils.normalizeAngle(t + math.pi), angSegment):
               # I translate and rotate the point to bring it back to the original position (with the center and rotation of the original ellipse)
               p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
               qad_utils.appendUniquePointToList(result, p)

      return result


   # ===============================================================================
   # methods for ellipses - end
   # methods for ellipse arcs - start
   # ===============================================================================


   # ============================================================================
   # fromPointToEllipseArc
   # ============================================================================
   @staticmethod
   def fromPointToEllipseArc(pt, ellipseArc):
      """the function returns the perpendicular projection of point on an arc of ellipse"""
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      perpPtList = QadPerpendicularity.fromPointToEllipse(pt, ellipse)
      for perpPt in perpPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(perpPt):
            result.append(perpPt)
      return result


   # ============================================================================
   # fromPointToBasicGeomObject
   # ============================================================================
   @staticmethod
   def fromPointToBasicGeomObject(pt, object):
      """the function returns the perpendicular projection of a point onto a basic geometric object:
            line, arc, ellipse arc, circle, ellipse.
      """
      if object.whatIs() == "LINE":
         res = QadPerpendicularity.fromPointToLine(pt, object)
         return [] if res is None else [res]
      elif object.whatIs() == "CIRCLE":
         return QadPerpendicularity.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         return QadPerpendicularity.fromPointToArc(pt, object)
      elif object.whatIs() == "ELLIPSE":
         return QadPerpendicularity.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         return QadPerpendicularity.fromPointToEllipseArc(pt, object)

      return []


   # ============================================================================
   # fromPointToBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def fromPointToBasicGeomObjectExtensions(pt, object):
      """the function returns the perpendicular projections of points on an extension of a basic geometric object:
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
      """
      if object.whatIs() == "LINE":
         res = QadPerpendicularity.fromPointToInfinityLine(pt, object)
         return [] if res is None else [res]
      elif object.whatIs() == "CIRCLE":
         return QadPerpendicularity.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object.center, object.radius)
         return QadPerpendicularity.fromPointToCircle(pt, circle)
      elif object.whatIs() == "ELLIPSE":
         return QadPerpendicularity.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object.center, object.majorAxisFinalPt, object.axisRatio)
         return QadPerpendicularity.fromPointToEllipse(pt, ellipse)

      return []


   # ============================================================================
   # fromPointToGeomObject
   # ============================================================================
   @staticmethod
   def fromPointToGeomObject(pt, object):
      """the function returns the perpendicular projection of a point onto a geometric object"""
      geomType = object.whatIs()
      result = []

      if geomType == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToBasicGeomObject(pt, linearObj))

      elif geomType == "POLYLINE":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToBasicGeomObject(pt, linearObj))

      elif geomType == "POLYGON":
         for subGeomAt in range(0, object.qty()):
            closedObj = object.getClosedObjectAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToGeomObject(pt, closedObj))

      elif geomType == "MULTI_POLYGON":
         for geomAt in range(0, object.qty()):
            polygon = object.getPolygonAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToGeomObject(pt, polygon))

      # object is a basic geometry
      else:
         result.extend(QadPerpendicularity.fromPointToBasicGeomObject(pt, object))

      return result


# ===============================================================================
# QadMinDistance class
# represents a class that calculates the minimum distance between basic objects: point, line, arc, ellipse arc, circle, ellipse
# ===============================================================================
class QadMinDistance():

   def __init__(self):
      pass


   # ===============================================================================
   # methods for infinite lines - start
   # ===============================================================================


   # ===============================================================================
   # fromInfinityLineToPoint
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToPoint(infinityLine, pt):
      """the function returns the minimum distance and the minimum distance point between an infinite line and a point
            (<minimum distance><minimum distance point>)
      """
      if infinityLine.isPtOnInfinityLine(pt) == True:
         return [0, pt]
      perpPt = QadPerpendicularity.fromPointToInfinityLine(pt, infinityLine)
      return [qad_utils.getDistance(perpPt, pt), perpPt]


   # ===============================================================================
   # fromInfinityLineToLine
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToLine(infinityLine, line):
      """the function returns the minimum distance and the minimum distance points between an infinite line and a segment
            (<minimum distance><minimum distance point on infinite line><minimum distance point on segment>)
      """
      intPt = QadIntersections.infinityLineWithLine(infinityLine, line)
      if intPt is not None:
         return [0, intPt, intPt]

      # returns a list: (<minimum distance><minimum distance point>)
      dist, ptLine = QadMinDistance.fromInfinityLineToPoint(infinityLine, line.pt1)
      bestResult = [dist, ptLine, line.pt1]

      dist, ptLine = QadMinDistance.fromInfinityLineToPoint(infinityLine, line.pt2)
      if bestResult[0] > dist:
         bestResult = [dist, ptLine, line.pt2]

      return bestResult[0], bestResult[1], bestResult[2]


   # ===============================================================================
   # fromInfinityLineToCircle
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToCircle(infinityLine, circle):
      """the function returns the minimum distance and the minimum distance points between an infinite line and a circle
            (<minimum distance><minimum distance point on infinite line><minimum distance point on circle>)
      """
      intPts = QadIntersections.infinityLineWithCircle(infinityLine, circle)
      if len(intPts) > 0:
         return [0, intPts[0], intPts[0]]

      perpPt = QadPerpendicularity.fromPointToInfinityLine(circle.center, infinityLine)
      angle = qad_utils.getAngleBy2Pts(circle.center, perpPt)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)

      return [qad_utils.getDistance(perpPt, ptOnCircle), perpPt, ptOnCircle]


   # ===============================================================================
   # fromInfinityLineToArc
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToArc(infinityLine, arc):
      """the function returns the minimum distance and the minimum distance points between an infinite line and an arc
            (<minimum distance><minimum distance point on infinite line><minimum distance point on arc>)
      """
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      result = QadMinDistance.fromInfinityLineToCircle(infinityLine, circle)
      ptArc = result[2]
      if arc.isPtOnArcOnlyByAngle(ptArc):
         return result

      d1 = qad_utils.getDistance(arc.gtStartPt(), ptOnCircle)
      res1 = QadMinDistance.fromInfinityLineToPoint(infinityLine, arc.getStartPt())
      res2 = QadMinDistance.fromInfinityLineToPoint(infinityLine, arc.getEndPt())
      if res1[0] < res2[0]:
         return [res1[0], res1[1], arc.getStartPt()]
      else:
         return [res2[0], res2[1], arc.getEndPt()]


   @staticmethod
   def distanza_infinityLine_ellipse(params, px, py, dx, dy, a, b, theta, h, k):
      t, phi = params
      # Parameters of the line: point on the line (px, py) and direction vector (dx, dy)
      # Ellipse parameters: semi-axes a, b, rotation angle theta, center (h, k)
      # px, py, a, b, theta, h, k = line_ellipse
      # Point on the line
      x_retta = px + t * dx
      y_retta = py + t * dy
      # Point on the ellipse (parameterized by phi)
      x_ellisse = h + a * np.cos(phi) * np.cos(theta) - b * np.sin(phi) * np.sin(theta)
      y_ellisse = k + a * np.cos(phi) * np.sin(theta) + b * np.sin(phi) * np.cos(theta)
      # Quadratic distance
      distanza2 = (x_retta - x_ellisse)**2 + (y_retta - y_ellisse)**2
      return distanza2


   # ===============================================================================
   # fromInfinityLineToEllipse chatgpt
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToEllipse(line, ellipse):
      """the function returns the minimum distance and the minimum distance points between an infinite line and an ellipse
            (<minimum distance><minimum distance point on infinite line><minimum distance point on ellipse>)
      """
      if NO_SCIPY == True: return []

      # test
#       line = QadLine()
#       line.set(QgsPointXY(1,1), QgsPointXY(2, 1))
#
#       ellipse = QadEllipse()
#       center = QgsPointXY(2, 1)
#       angle = np.pi / 6  # 30 gradi
#       a = 5
#       b = 3
#       majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, angle, a)
#       ellipse.set(center, majorAxisFinalPt, b / a)



      # Parameters of the line: point on the line (px, py) and direction vector (dx, dy)
      px, py = line.getStartPt().x(), line.getStartPt().y()
      dx, dy = line.getEndPt().x() - px, line.getEndPt().y() - py

      # Calculate the length of the major axis (a)
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt)
      # Calculate the length of the minor axis (b)
      b = a * ellipse.axisRatio
      # theta: the rotation angle of the ellipse.
      theta = ellipse.getRotation()
      # h and k: the translations of the ellipse with respect to the origin, center coordinates
      h = ellipse.center.x()
      k = ellipse.center.y()

      args = (px, py,  dx, dy, a, b, theta, h, k)

      # Initial estimate for t and phi
      stima_iniziale = [0, 0]

      # Minimization of the quadratic distance function
      risultato = minimize(QadMinDistance.distanza_infinityLine_ellipse, stima_iniziale, args, method='Nelder-Mead')

      # Estrazione dei risultati
      t_min, phi_min = risultato.x

      # Calculation of minimum distance points
      x_retta_min = px + t_min * dx
      y_retta_min = py + t_min * dy
      x_ellisse_min = h + a * np.cos(phi_min) * np.cos(theta) - b * np.sin(phi_min) * np.sin(theta)
      y_ellisse_min = k + a * np.cos(phi_min) * np.sin(theta) + b * np.sin(phi_min) * np.cos(theta)

      ptRetta = QgsPointXY(x_retta_min, y_retta_min)
      ptEllisse = QgsPointXY(x_ellisse_min, y_ellisse_min)

      return qad_utils.getDistance(ptRetta, ptEllisse), ptRetta, ptEllisse



   # ===============================================================================
   # fromInfinityLineToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToEllipseArc(line, ellipseArc):
      """the function returns the minimum distance and the minimum distance points between an infinite line and an arc of an ellipse
            (<minimum distance><minimum distance point on an infinite line><minimum distance point on an ellipse arc>)
      """
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      result = QadMinDistance.fromInfinityLineToEllipse(infinityLine, ellipse)
      ptArc = result[2]
      if ellipseArc.isPtOnEllipseArcOnlyByAngle(ptArc):
         return result

      d1 = qad_utils.getDistance(arc.gtStartPt(), ptOnCircle)
      res1 = QadMinDistance.fromInfinityLineToPoint(infinityLine, ellipseArc.getStartPt())
      res2 = QadMinDistance.fromInfinityLineToPoint(infinityLine, ellipseArc.getEndPt())
      if res1[0] < res2[0]:
         return [res1[0], res1[1], ellipseArc.getStartPt()]
      else:
         return [res2[0], res2[1], ellipseArc.getEndPt()]


   # ===============================================================================
   # methods for infinite lines - end
   # segment methods - start
   # ===============================================================================


   # ===============================================================================
   # fromLineToPoint
   # ===============================================================================
   @staticmethod
   def fromLineToPoint(line, pt):
      """the function returns the minimum distance and the minimum distance points between a segment and a point
            (<minimum distance><minimum distance point>)
      """
      if line.containsPt(pt) == True:
         return [0, pt]
      perpPt = QadPerpendicularity.fromPointToInfinityLine(pt, line)
      if perpPt is not None:
         if line.containsPt(perpPt) == True:
            return [qad_utils.getDistance(perpPt, pt), perpPt]

      distFromP1 = qad_utils.getDistance(line.pt1, pt)
      distFromP2 = qad_utils.getDistance(line.pt2, pt)
      if distFromP1 < distFromP2:
         return [distFromP1, line.pt1]
      else:
         return [distFromP2, line.pt2]


   # ===============================================================================
   # fromTwoLines
   # ===============================================================================
   @staticmethod
   def fromTwoLines(line1, line2):
      """the function returns the minimum distance and the minimum distance points between 2 segments
            (<minimum distance><minimum distance point on segment1><minimum distance point on segment2>)
      """
      intPt = QadIntersections.twoLines(line1, line2)
      if intPt is not None:
         return [0, intPt, intPt]

      # returns a list: (<minimum distance><minimum distance point>)
      result = QadMinDistance.fromLineToPoint(line2, line1.pt1)
      dist = result[0]
      ptLine = result[1]
      bestResult = [dist, line1.pt1, ptLine]

      result = QadMinDistance.fromLineToPoint(line2, line1.pt2)
      dist = result[0]
      ptLine = result[1]
      if bestResult[0] > dist:
         bestResult = [dist, line1.pt2, ptLine]

      result = QadMinDistance.fromLineToPoint(line1, line2.pt1)
      dist = result[0]
      ptLine = result[1]
      if bestResult[0] > dist:
         bestResult = [dist, ptLine, line2.pt1]

      result = QadMinDistance.fromLineToPoint(line1, line2.pt2)
      dist = result[0]
      ptLine = result[1]
      if bestResult[0] > dist:
         bestResult = [dist, ptLine, line2.pt2]

      return [bestResult[0], bestResult[1], bestResult[2]]


   # ===============================================================================
   # fromLineToCircle
   # ===============================================================================
   @staticmethod
   def fromLineToCircle(line, circle):
      """the function returns the minimum distance and the minimum distance points between a segment and a circle
            (<minimum distance><minimum distance point on line><minimum distance point on circle>)
      """
      intPts = QadIntersections.lineWithCircle(line, circle)
      if len(intPts) > 0:
         return [0, intPts[0], intPts[0]]

      d1 = qad_utils.getDistance(line.getStartPt(), circle.center)
      if d1 < circle.radius: # line inside the circle
         d2 = qad_utils.getDistance(line.getEndPt(), circle.center)
         if d1 > d2:
            ptLine = line.getStartPt()
         else:
            ptLine = line.getEndPt()
      else: # line outside the circle
         result = QadMinDistance.fromInfinityLineToCircle(line, circle)
         if line.containsPt(result[1]):
            return result
         else:
            d2 = qad_utils.getDistance(line.getEndPt(), circle.center)
            if d1 < d2:
               ptLine = line.getStartPt()
            else:
               ptLine = line.getEndPt()

      angle = qad_utils.getAngleBy2Pts(circle.center, ptLine)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)

      return [qad_utils.getDistance(ptLine, ptOnCircle), ptLine, ptOnCircle]


   # ===============================================================================
   # fromLineToArc
   # ===============================================================================
   @staticmethod
   def fromLineToArc(line, arc):
      """the function returns the minimum distance and the minimum distance points between a segment and an arc
            (<minimum distance><minimum distance point on line><minimum distance point on arc>)
      """
      intPtList = QadIntersections.lineWithArc(line, arc)
      if len(intPtList) > 0:
         return [0, intPtList[0], intPtList[0]]

      p1Line = line.getStartPt()
      p2Line = line.getEndPt()
      resultP1 = QadMinDistance.fromArcToPoint(arc, p1Line) # returns (<minimum distance><minimum distance point on arc>)
      resultP2 = QadMinDistance.fromArcToPoint(arc, p2Line) # returns (<minimum distance><minimum distance point on arc>)

      # if the segment is inside the circle created by the extension of the arc
      if qad_utils.getDistance(p1Line, arc.center) < arc.radius and \
         qad_utils.getDistance(p2Line, arc.center) < arc.radius:
         if resultP1[0] < resultP2[0]: # if the starting point of the line is closer to the arc
            return [resultP1[0], p1Line, resultP1[1]]
         else:
            return [resultP2[0], p2Line, resultP2[1]]

      else: # if the segment is outside the circle originated by the extension of the arc
         perpPt = QadPerpendicularity.fromPointToLine(arc.center, line)
         if perpPt is not None:
            angle = qad_utils.getAngleBy2Pts(arc.center, perpPt)
            # if the point of perpendicular to the <line> segment is included between the arc angles
            if arc.isAngleBetweenAngles(angle):
               ptOnArc = qad_utils.getPolarPointByPtAngle(arc.center, angle, arc.radius)
               return [qad_utils.getDistance(perpPt, ptOnArc), perpPt, ptOnArc]

         bestResult = resultP1 # (<minimum distance><minimum distance point on arc>)
         bestResult.insert(1, p1Line) # (<minimum distance><minimum distance point on line><minimum distance point on arc>)
         resultP2.insert(1, p2Line)
         if bestResult[0] > resultP2[0]:
            bestResult = resultP2

         ptStart = arc.getStartPt()
         ptEnd = arc.getEndPt()

         resultStartPt = QadMinDistance.fromLineToPoint(line, ptStart) # (<minimum distance><minimum distance point on line>
         resultStartPt.append(ptStart) # <minimum distance><minimum distance point><minimum distance on line><minimum distance point on arc>
         if bestResult[0] > resultStartPt[0]:
            bestResult = resultStartPt

         resultEndPt = QadMinDistance.fromLineToPoint(line, ptEnd) # (<minimum distance><minimum distance point on line>
         resultEndPt.append(ptEnd) # <minimum distance><minimum distance point><minimum distance on line><minimum distance point on arc>
         if bestResult[0] > resultEndPt[0]:
            bestResult = resultEndPt

         return bestResult # (<minimum distance><minimum distance point on line><minimum distance point on arc>)


   @staticmethod
   def distanza_line_ellipse(params, line, ellipse):
      t, theta = params
      x_segment = (1 - t) * line.getStartPt().x() + t * line.getEndPt().x()
      y_segment = (1 - t) * line.getStartPt().y() + t * line.getEndPt().y()

      pt_ellipse = ellipse.getPointAtAngle(theta)
      x_ellipse = pt_ellipse.x()
      y_ellipse = pt_ellipse.y()

      return np.sqrt((x_segment - x_ellipse) ** 2 + (y_segment - y_ellipse) ** 2)


   # ===============================================================================
   # fromLineToEllipse chatgpt
   # ===============================================================================
   @staticmethod
   def fromLineToEllipse(line, ellipse):
      """the function returns the minimum distance and the minimum distance points between a segment and an ellipse
            (<minimum distance><minimum distance point on line><minimum distance point on ellipse>)
      """
      if NO_SCIPY == True: return []

      initial_guess = [0.5, 0]
      bounds = [(0, 1), (0, 2 * np.pi)]

      args = (line, ellipse)

      result = minimize(QadMinDistance.distanza_line_ellipse, initial_guess, args, bounds=bounds)

      if result.success:
        t_opt, theta_opt = result.x
        x_segment_opt = (1 - t_opt) * line.getStartPt().x() + t_opt * line.getEndPt().x()
        y_segment_opt = (1 - t_opt) * line.getStartPt().y() + t_opt * line.getEndPt().y()

        pt_ellipse = ellipse.getPointAtAngle(theta_opt)
        x_ellipse_opt = pt_ellipse.x()
        y_ellipse_opt = pt_ellipse.y()

        min_distance = result.fun

        return [min_distance, QgsPointXY(x_segment_opt, y_segment_opt), QgsPointXY(x_ellipse_opt, y_ellipse_opt)]
      else:
         raise []


   # ===============================================================================
   # fromLineToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromLineToEllipseArc(line, ellipseArc):
      """the function returns the minimum distance and the minimum distance points between a segment and an arc of an ellipse
            (<minimum distance><minimum distance point on line><minimum distance point on ellipse arc>)
      """

      pass # TODO


   # ===============================================================================
   # segment methods - end
   # methods for circles - start
   # ===============================================================================


   # ===============================================================================
   # fromCircleToPoint
   # ===============================================================================
   @staticmethod
   def fromCircleToPoint(circle, pt):
      """the function returns the minimum distance and the minimum distance points between a circle and a point
            (<minimum distance><minimum distance point>)
      """
      angle = qad_utils.getAngleBy2Pts(circle.center, pt)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)

      return [qad_utils.getDistance(pt, ptOnCircle), ptOnCircle]


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def fromTwoCircles(circle1, circle2):
      """the function returns the minimum distance and the minimum distance points between 2 circles
            (<minimum distance><minimum distance point on circle1><minimum distance point on circle2>)
      """
      intersections = QadIntersections.twoCircles(circle1, circle2)
      if len(intersections) > 0:
         return [0.0, intersections[0], intersections[0]]

      angle = qad_utils.getAngleBy2Pts(circle1.center, circle2.center)
      pt1Circle1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
      pt2Circle1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, -circle1.radius)
      pt1Circle2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, circle2.radius)
      pt2Circle2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, -circle2.radius)

      minDistance = qad_utils.getDistance(pt1Circle1, pt1Circle2)
      ptMinDistanceCircle1 = pt1Circle1
      ptMinDistanceCircle2 = pt1Circle2

      dist = qad_utils.getDistance(pt1Circle1, pt2Circle2)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle1 = pt1Circle1
         ptMinDistanceCircle2 = pt2Circle2

      dist = qad_utils.getDistance(pt2Circle1, pt1Circle2)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle1 = pt2Circle1
         ptMinDistanceCircle2 = pt1Circle2

      dist = qad_utils.getDistance(pt2Circle1, pt2Circle2)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle1 = pt2Circle1
         ptMinDistanceCircle2 = pt2Circle2

      return [minDistance, ptMinDistanceCircle1, ptMinDistanceCircle2]


   # ===============================================================================
   # fromCircleToArc
   # ===============================================================================
   @staticmethod
   def fromCircleToArc(circle, arc):
      """the function returns the minimum distance and the minimum distance points between a circle and an arc
            (<minimum distance><minimum distance point on circle><minimum distance point on arc>)
      """
      intersections = QadIntersections.circleWithArc(circle, arc)
      if len(intersections) > 0:
         return [0.0, intersections[0], intersections[0]]

      pt1Arc = arc.getStartPt()
      pt2Arc = arc.getEndPt()

      angle = qad_utils.getAngleBy2Pts(circle.center, pt1Arc)
      ptCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      minDistance = qad_utils.getDistance(ptCircle, pt1Arc)
      ptMinDistanceCircle = ptCircle
      ptMinDistanceArc = pt1Arc

      angle = qad_utils.getAngleBy2Pts(circle.center, pt2Arc)
      ptCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      dist = qad_utils.getDistance(ptCircle, pt2Arc)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle = ptCircle
         ptMinDistanceArc = pt2Arc

      line = QadLine()
      line.set(circle.center, arc.center)
      intersections = QadIntersections.infinityLineWithArc(line, arc)
      if len(intersections) > 0:
         angle = qad_utils.getAngleBy2Pts(circle.center, arc.center)
         ptCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
         dist = qad_utils.getDistance(ptCircle, intersections[0])
         if dist < minDistance:
            minDistance = dist
            ptMinDistanceCircle = ptCircle
            ptMinDistanceArc = intersections[0]

      return [minDistance, ptMinDistanceCircle, ptMinDistanceArc]


   # ===============================================================================
   # fromCircleToEllipse
   # ===============================================================================
   @staticmethod
   def fromCircleToEllipse(circle, ellipse):
      """the function returns the minimum distance and the minimum distance points between a circle and an ellipse
            (<minimum distance><minimum distance point on circle><minimum distance point on ellipse>)
      """
      pass # TODO


   # ===============================================================================
   # fromCircleToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromCircleToEllipseArc(circle, ellipseArc):
      """the function returns the minimum distance and the minimum distance points between a circle and an arc of an ellipse
            (<minimum distance><minimum distance point on circle><minimum distance point on ellipse arc>)
      """
      pass # TODO


   # ===============================================================================
   # methods for circles - end
   # methods for arcs - start
   # ===============================================================================


   # ===============================================================================
   # fromArcToPoint
   # ===============================================================================
   @staticmethod
   def fromArcToPoint(arc, pt):
      """the function returns the minimum distance and the minimum distance points between an arc and a point
            (<minimum distance><minimum distance point>)
      """
      if arc.isPtOnArcOnlyByAngle(pt):
         circle = QadCircle()
         circle.set(arc.center, arc.radius)
         return QadMinDistance.fromCircleToPoint(circle, pt)
      else:
         p1 = arc.getStartPt()
         p2 = arc.getEndPt()
         d1 = qad_utils.getDistance(p1, pt)
         d2 = qad_utils.getDistance(p2, pt)
         if d1 < d2:
            return [d1, p1]
         else:
            return [d2, p2]

      angle = qad_utils.getAngleBy2Pts(circle.center, pt)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)

      return [qad_utils.getDistance(pt, ptOnCircle), ptOnCircle]


   # ===============================================================================
   # fromTwoArcs
   # ===============================================================================
   @staticmethod
   def fromTwoArcs(arc1, arc2):
      """the function returns the minimum distance and the minimum distance points between 2 arcs
            (<minimum distance><minimum distance point on arc1><minimum distance point on arc2>)
      """
      intPtList = QadIntersections.twoArcs(arc1, arc2)
      if len(intPtList) > 0:
         return [0, intPtList[0], intPtList[0]]

      StartPtArc1 = arc1.getStartPt()
      EndPtArc1 = arc1.getEndPt()
      StartPtArc2 = arc2.getStartPt()
      EndPtArc2 = arc2.getEndPt()

      # calculate the minimum distance between the ends of one arc and the other arc e
      # I choose the best of the four distances
      # returns a list: (<minimum distance><nearest point>)
      dummy = QadMinDistance.fromArcToPoint(arc2, StartPtArc1)
      bestResult = [dummy[0], StartPtArc1, dummy[1]]

      dummy = QadMinDistance.fromArcToPoint(arc2, EndPtArc1)
      resultArc2_EndPtArc1 = [dummy[0], EndPtArc1, dummy[1]]
      if bestResult[0] > resultArc2_EndPtArc1[0]:
         bestResult = resultArc2_EndPtArc1

      dummy = QadMinDistance.fromArcToPoint(arc1, StartPtArc2)
      resultArc1_StartPtArc2 = [dummy[0], dummy[1], StartPtArc2]
      if bestResult[0] > resultArc1_StartPtArc2[0]:
         bestResult = resultArc1_StartPtArc2

      dummy = QadMinDistance.fromArcToPoint(arc1, EndPtArc2)
      resultArc1_EndPtArc2 = [dummy[0], dummy[1], EndPtArc2]
      if bestResult[0] > resultArc1_EndPtArc2[0]:
         bestResult = resultArc1_EndPtArc2

      # circle1 and circle 2 are derived from the extension of arc1 and arc2 respectively.
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)
      distanceBetweenCenters = qad_utils.getDistance(circle1.center, circle2.center)

      # considero i seguenti 2 casi:
      # i cerchi sono esterni
      if distanceBetweenCenters - circle1.radius - circle2.radius > 0:
         # create a segment that joins the two centers and intersects it with arc 1
         l = QadLine()
         l.set(arc1.center, arc2.center)
         intPtListArc1 = QadIntersections.lineWithArc(l, arc1)
         if len(intPtListArc1) > 0:
            intPtArc1 = intPtListArc1[0]

            # create a segment that joins the two centers and intersects it with arc 2
            intPtListArc2 = QadIntersections.lineWithArc(l, arc2)
            if len(intPtListArc2) > 0:
               intPtArc2 = intPtListArc2[0]

               distanceIntPts = qad_utils.getDistance(intPtArc1, intPtArc2)
               if bestResult[0] > distanceIntPts:
                  bestResult = [distanceIntPts, intPtArc1, intPtArc2]
      # circle1 is inside circle2 or
      # circle2 is inside circle1
      elif distanceBetweenCenters + circle1.radius < circle2.radius or \
           distanceBetweenCenters + circle2.radius < circle1.radius:
         # create a segment that joins the two centers and intersects it with arc 2
         l = QadLine()
         l.set(arc1.center, arc2.center)
         intPtListArc2 = QadIntersections.infinityLineWithArc(l, arc2)
         if len(intPtListArc2) > 0:
            # create a segment that joins the two centers and intersects it with arc 1
            intPtListArc1 = QadIntersections.infinityLineWithArc(l, arc1)

            for intPtArc2 in intPtListArc2:
               for intPtArc1 in intPtListArc1:
                  distanceIntPts = qad_utils.getDistance(intPtArc2, intPtArc1)
                  if bestResult[0] > distanceIntPts:
                     bestResult = [distanceIntPts, intPtArc1, intPtArc2]

      return bestResult


   # ===============================================================================
   # fromArcToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromArcToEllipseArc(arc, ellipseArc):
      """the function returns the minimum distance and the minimum distance points between an arc and an ellipse arc
            (<minimum distance><point of minimum distance on arc><point of minimum distance on arc of ellipse>)
      """
      pass # TODO


   # ===============================================================================
   # methods for arcs - end
   # methods for ellipses - start
   # ===============================================================================


   # ===============================================================================
   # fromEllipseToPoint
   # ===============================================================================
   @staticmethod
   def fromEllipseToPoint(ellipse, pt):
      """the function returns the minimum distance and the minimum distance points between an ellipse and a point
            (<minimum distance><minimum distance point>)
      """
      perpPts = QadPerpendicularity.fromPointToEllipse(pt, ellipse)
      dist = sys.float_info.max
      for perpPt in perpPts:
         d = qad_utils.getDistance(pt, perpPt)
         if d < dist:
            dist = d
            bestPt = perpPt

      return [dist, bestPt]


   # ===============================================================================
   # fromTwoEllipses
   # ===============================================================================
   @staticmethod
   def fromTwoEllipses(ellipse1, ellipse2):
      """the function returns the minimum distance and the minimum distance points between 2 ellipses
            (<minimum distance><minimum distance point on ellipse1><minimum distance point on ellipse2>)
      """
      pass # TODO


   # ===============================================================================
   # fromEllipseToArc
   # ===============================================================================
   @staticmethod
   def fromEllipseToArc(ellipse, arc):
      """the function returns the minimum distance and the minimum distance points between an ellipse and an arc
            (<minimum distance><minimum distance point on ellipse><minimum distance point on arc>)
      """
      pass # TODO


   # ===============================================================================
   # fromEllipseToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromEllipseToEllipseArc(ellipse, ellipseArc):
      """the function returns the minimum distance and the minimum distance points between an ellipse and an arc of an ellipse
            (<minimum distance><minimum distance point on ellipse><minimum distance point on ellipse arc>)
      """
      pass # TODO


   # ===============================================================================
   # methods for ellipses - end
   # methods for ellipse arcs - start
   # ===============================================================================


   # ===============================================================================
   # fromEllipseArcToPoint
   # ===============================================================================
   @staticmethod
   def fromEllipseArcToPoint(ellipseArc, pt):
      """the function returns the minimum distance and the minimum distance points between an arc of an ellipse and a point
            (<minimum distance><minimum distance point>)
      """
      perpPts = QadPerpendicularity.fromPointToEllipseArc(pt, ellipseArc)
      dist = sys.float_info.max
      for perpPt in perpPts:
         d = qad_utils.getDistance(pt, perpPt)
         if d < dist:
            dist = d
            bestPt = perpPt

      if dist < sys.float_info.max: return [dist, bestPt]

      d1 = qad_utils.getDistance(pt, ellipseArc.getStartPt())
      d2 = qad_utils.getDistance(pt, ellipseArc.getEndPt())

      if d1 < d2:
         return [d1, ellipseArc.getStartPt()]
      else:
         return [d2, ellipseArc.getEndPt()]


   # ===============================================================================
   # fromTwoEllipseArcs
   # ===============================================================================
   @staticmethod
   def fromTwoEllipseArcs(ellipseArc1, ellipseArc2):
      """the function returns the minimum distance and the minimum distance points between 2 ellipse arcs
            (<minimum distance><minimum distance point on arc ellipse1><minimum distance point on arc ellipse2>)
      """
      pass # TODO


   # ============================================================================
   # fromPointToBasicGeomObject
   # ============================================================================
   @staticmethod
   def fromPointToBasicGeomObject(pt, object):
      """the function returns the minimum distance and the minimum distance point between a basic geometric object and a point
            (<minimum distance><minimum distance point>)
      """
      if object.whatIs() == "POINT":
         return (object.distance(pt), object)
      elif object.whatIs() == "LINE":
         return QadMinDistance.fromLineToPoint(object, pt)
      elif object.whatIs() == "CIRCLE":
         return QadMinDistance.fromCircleToPoint(object, pt)
      elif object.whatIs() == "ARC":
         return QadMinDistance.fromArcToPoint(object, pt)
      elif object.whatIs() == "ELLIPSE":
         return QadMinDistance.fromEllipseToPoint(object, pt)
      elif object.whatIs() == "ELLIPSE_ARC":
         return QadMinDistance.fromEllipseArcToPoint(object, pt)

      return []


   # ============================================================================
   # fromPointToBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def fromPointToBasicGeomObjectExtensions(pt, object):
      """the function returns the minimum distance and the minimum distance point between an extension of the basic geometric object and a point
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
      """
      if object.whatIs() == "LINE":
         return QadMinDistance.fromInfinityLineToPoint(object, pt)
      elif object.whatIs() == "CIRCLE":
         return QadMinDistance.fromCircleToPoint(object, pt)
      elif object.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object.center, object.radius)
         return QadMinDistance.fromCircleToPoint(circle, pt)
      elif object.whatIs() == "ELLIPSE":
         return QadMinDistance.fromEllipseToPoint(object, pt)
      elif object.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object.center, object.majorAxisFinalPt, object.axisRatio)
         return QadMinDistance.fromEllipseToPoint(object, pt)

      return []


   # ============================================================================
   # fromTwoBasicGeomObjects
   # ============================================================================
   @staticmethod
   def fromTwoBasicGeomObjects(object1, object2):
      """the function returns
            <minimum distance>
            <minimum distance point on object1>
            <minimum distance point on object2>
            of the 2 basic geometric objects: line, arc, ellipse arc, circle, ellipse.
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            # <minimum distance><minimum distance point on segment1><minimum distance point on segment2>
            return QadMinDistance.fromTwoLines(object1, object2)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromLineToCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromLineToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromLineToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromLineToEllipseArc(object1, object2)

      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromTwoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromCircleToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromCircleToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromCircleToEllipseArc(object1, object2)

      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromTwoArcs(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromEllipseToArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromArcToEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromEllipseToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromTwoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromEllipseToEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToEllipseArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipseArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromArcToEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromEllipseToEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromTwoEllipseArcs(object1, object2)

      return []


   # ============================================================================
   # fromTwoGeomObjects
   # ============================================================================
   @staticmethod
   def fromTwoGeomObjects(object1, object2):
      """the function returns
            <minimum distance>
            <minimum distance point on object1>
            <geomIndex on object1>
            <subGeomIndex on object1>
            <partIndex on object1>
            <minimum distance point on object2>
            <geomIndex on object2>
            <subGeomIndex on object2>
            <partIndex on object2>
            of the 2 geometric objects.
      """
      minDistancePts = None
      geomType1 = object1.whatIs()

      if geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getLinearObjectAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt

      elif geomType1 == "POLYLINE":
         for partAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getLinearObjectAt(partAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[4] = partAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[4] = partAt

      elif geomType1 == "POLYGON":
         for subGeomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getClosedObjectAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[3] = subGeomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[3] = subGeomAt

      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getPolygonAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt

      elif geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getPointAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt

      # object1 is a basic geometry
      else:
         geomType2 = object2.whatIs()

         if geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getLinearObjectAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt

         elif geomType2 == "POLYLINE":
            for partAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getLinearObjectAt(partAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[8] = partAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[8] = partAt

         elif geomType2 == "POLYGON":
            for subGeomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getClosedObjectAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[7] = subGeomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[7] = subGeomAt

         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getPolygonAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt

         elif geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getPointAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt

         # object2 is a basic geometry (and object1 was also a basic geometry)
         else:
            dummy = QadMinDistance.fromTwoBasicGeomObjects(object1, object2)
            minDistancePts = [dummy[0], dummy[1], 0, 0, 0, dummy[2], 0, 0, 0,]

      return minDistancePts


   # ============================================================================
   # twoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def fromTwoBasicGeomObjectExtensions(object1, object2):
      """the function returns the minimum distance and the minimum distance points of the extensions of 2 basic geometric objects:
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromInfinityLineToCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadMinDistance.fromInfinityLineToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromInfinityLineToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromInfinityLineToEllipseArc(object1, object2)

      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromTwoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadMinDistance.fromCircleToArc(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromCircleToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromCircleToEllipse(object1, ellipse)

      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToCircle(object2, circle1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromTwoCircles(object2, circle1)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadMinDistance.fromTwoCircles(circle1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromCircleToEllipse(circle1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromCircleToEllipse(circle1, ellipse)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadMinDistance.fromCircleToEllipse(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromTwoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromEllipseToEllipseArc(object1, ellipse)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToEllipse(object2, ellipse1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipse(object2, ellipse1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object.center, object.radius)
            return QadMinDistance.fromCircleToEllipse(circle, ellipse1)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromTwoEllipses(ellipse1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromTwoEllipseArcs(ellipse1, ellipse2)

      return []


# ===============================================================================
# QadTangency class
# represents a class that calculates the tangency between basic objects: point, line, circle, arc, ellipse, arc of ellipse
# ===============================================================================
class QadTangency():

   def __init__(self):
      pass


   # ===============================================================================
   # methods for circles - start
   # ===============================================================================


   # ===============================================================================
   # fromPointToCircle
   # ===============================================================================
   @staticmethod
   def fromPointToCircle(point, circle):
      """the function returns a list of tangency points on the circle of lines passing through a point"""
      dist = circle.center.distance(point)
      if dist < circle.radius: return []

      angleOffSet = math.asin(circle.radius / dist)
      angleOffSet = (math.pi / 2) - angleOffSet
      angle = qad_utils.getAngleBy2Pts(circle.center, point)

      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, angle + angleOffSet, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(circle.center, angle - angleOffSet, circle.radius)
      return [pt1, pt2]


   # ============================================================================
   # twoCircles
   # ============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """the function returns a list of lines that are tangents to the two circles"""
      x1 = circle1.center[0]
      y1 = circle1.center[1]
      r1 = circle1.radius
      x2 = circle2.center[0]
      y2 = circle2.center[1]
      r2 = circle2.radius

      d_sq = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)
      if (d_sq <= (r1-r2)*(r1-r2)):
          return []

      d = math.sqrt(d_sq);
      vx = (x2 - x1) / d;
      vy = (y2 - y1) / d;

      tangents = []
      # Let A, B be the centers, and C, D be points at which the tangent
      # touches first and second circle, and n be the normal vector to it.
      #
      # We have the system:
      #   n * n = 1          (n is a unit vector)
      #   C = A + r1 * n
      #   D = B +/- r2 * n
      #   n * CD = 0         (common orthogonality)
      #
      # n * CD = n * (AB +/- r2*n - r1*n) = AB*n - (r1 -/+ r2) = 0,  <=>
      # AB * n = (r1 -/+ r2), <=>
      # v * n = (r1 -/+ r2) / d,  where v = AB/|AB| = AB/d
      # This is a linear equation in unknown vector n.
      sign1 = +1
      while sign1 >= -1:
         c = (r1 - sign1 * r2) / d;

         # Now we're just intersecting a line with a circle: v*n=c, n*n=1

         if (c*c > 1.0):
            sign1 = sign1 - 2
            continue

         h = math.sqrt(max(0.0, 1.0 - c*c));

         sign2 = +1
         while sign2 >= -1:
            nx = vx * c - sign2 * h * vy;
            ny = vy * c + sign2 * h * vx;

            tangent = QadLine()
            tangent.set(QgsPointXY(x1 + r1 * nx, y1 + r1 * ny), \
                        QgsPointXY(x2 + sign1 * r2 * nx, y2 + sign1 * r2 * ny))
            tangents.append(tangent)
            sign2 = sign2 - 2

         sign1 = sign1 - 2

      return tangents


   # ============================================================================
   # fromCircleToArc
   # ============================================================================
   @staticmethod
   def fromCircleToArc(circle1, arc2):
      """the function returns a list of lines that are tangents to the circle and the arc"""
      result = []
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)
      lines = QadTangency.twoCircles(circle1, circle2)
      for line in lines:
         if arc2.isPtOnArcOnlyByAngle(line.getEndPt()):
            result.append(line)
      return result


   # ============================================================================
   # fromCircleToEllipse
   # ============================================================================
   @staticmethod
   def fromCircleToEllipse(circle1, ellipse2):
      """the function returns a list of lines that are tangents to the circle and the ellipse"""
      return []


   # ============================================================================
   # fromCircleToEllipseArc
   # ============================================================================
   @staticmethod
   def fromCircleToEllipseArc(circle1, ellipseArc2):
      """the function returns a list of lines that are tangents to the circle and the arc of the ellipse"""
      result = []
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadTangency.fromCircleToEllipse(circle1, ellipse2)
      for line in lines:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(line.getEndPt()):
            result.append(line)
      return result


   # ===============================================================================
   # methods for circles - end
   # methods for arcs - start
   # ===============================================================================


   # ============================================================================
   # fromPointToArc
   # ============================================================================
   @staticmethod
   def fromPointToArc(pt, arc):
      """the function returns a list of tangency points on the arc of lines passing through a point"""
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      tangPtList = QadTangency.fromPointToCircle(pt, circle)
      for tangPt in tangPtList:
         if arc.isPtOnArcOnlyByAngle(tangPt):
            result.append(tangPt)
      return result


   # ============================================================================
   # twoArcs
   # ============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """the function returns a list of lines that are tangents to the two arcs"""
      result = []
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadTangency.fromCircleToArc(circle1, arc2)
      for line in lines:
         if arc1.isPtOnArcOnlyByAngle(line.getStartPt()):
            result.append(line)
      return result


   # ============================================================================
   # fromArcToEllipse
   # ============================================================================
   @staticmethod
   def fromArcToEllipse(arc1, ellipse2):
      """the function returns a list of lines that are tangents to the arc and the ellipse"""
      result = []
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadTangency.fromCircleToEllipse(circle1, ellipse2)
      for line in lines:
         if arc1.isPtOnArcOnlyByAngle(line.getStartPt()):
            result.append(tangPt)
      return result


   # ============================================================================
   # fromArcToEllipseArc
   # ============================================================================
   @staticmethod
   def fromArcToEllipseArc(arc1, ellipseArc2):
      """the function returns a list of lines that are the tangents to the arc and the arc of the ellipse"""
      result = []
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadTangency.fromCircleToEllipseArc(circle1, ellipseArc2)
      for line in lines:
         if arc1.isPtOnArcOnlyByAngle(line.getStartPt()):
            result.append(line)
      return result


   # ===============================================================================
   # methods for arcs - end
   # methods for ellipses - start
   # ===============================================================================


   # ============================================================================
   # fromPointToEllipse
   # ============================================================================
   @staticmethod
   def fromPointToEllipse(pt, ellipse):
      """the function returns a list of tangent points on the ellipse of lines passing through a point"""
      # https://www3.ul.ie/~rynnet/swconics/TC.htm
      # 1. With the radius set to the major axis, scribe an arc  from F.
      # 2. From P write an arc with radius set to F1
      # 3. Where this arc intersects the previous arc drawn, draw the lines back to the focal point F.
      # 4. The points where these lines intersect the curve will be the points of contact of the tangents from point P.

      result = []
      line = QadLine()
      # trovo i fuochi
      foci = ellipse.getFocus()
      if len(foci) == 0: return result
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) * 2 # major axis
      b = a * ellipse.axisRatio # minor axis
      # points 1 and 2
      focus = foci[0] # I try with the first fire first
      circle1 = QadCircle()
      circle1.set(focus, a)
      circle2 = QadCircle()
      circle2.set(point, qad_utils.getDistance(foci[1], point))
      intPts = QadIntersections.twoCircles(circle1, circle2)
      if len(intPts) == 0: # if they have no intersections I try the other fire
         focus = foci[1]
         circle1.set(focus, a)
         circle2.set(point, qad_utils.getDistance(foci[0], point))
         intPts = QadIntersections.twoCircles(circle1, circle2)
         if len(intPts) == 0: # if they have no intersections hello
            return result

      if len(intPts) == 1:
         line.set(focus, intPts[0])
         tgPt1 = QadIntersections.lineWithEllipse(line, ellipse)
         if len(tgPt1) == 0: return result
         result.append(tgPt1[0])
      else:
         line.set(focus, intPts[0])
         tgPt1 = QadIntersections.lineWithEllipse(line, ellipse)
         line.set(focus, intPts[1])
         tgPt2 = QadIntersections.lineWithEllipse(line, ellipse)
         if len(tgPt1) == 0 or len(tgPt2) == 0: return result
         result.append(tgPt1[0])
         result.append(tgPt2[0])

      return result


   # ============================================================================
   # twoEllipses
   # ============================================================================
   @staticmethod
   def twoEllipses(ellipse1, ellipse2):
      """the function returns a list of lines that are the tangents to two ellipses"""
      # TODO
      return []


   # ============================================================================
   # fromEllipseToEllipseArc
   # ============================================================================
   @staticmethod
   def fromEllipseToEllipseArc(ellipse1, ellipseArc2):
      """the function returns a list of lines that are tangents to the ellipse and the arc of the ellipse"""
      result = []
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadTangency.twoEllipses(ellipse1, ellipse2)
      for line in lines:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(line.getEndPt()):
            result.append(line)
      return result


   # ===============================================================================
   # methods for ellipses - end
   # methods for ellipse arcs - start
   # ===============================================================================


   # ============================================================================
   # fromPointToEllipseArc
   # ============================================================================
   @staticmethod
   def fromPointToEllipseArc(pt, ellipseArc):
      """the function returns a list of tangency points on the ellipse arc of lines passing through a point"""
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      tangPtList = QadTangency.fromPointToEllipse(pt, ellipse)
      for tangPt in tangPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(tangPt):
            result.append(tangPt)
      return result


   # ============================================================================
   # twoEllipseArcs
   # ============================================================================
   @staticmethod
   def twoEllipseArcs(ellipseArc1, ellipseArc2):
      """the function returns a list of lines that are the tangents to two arcs of ellipses"""
      result = []
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      lines = QadTangency.fromEllipseToEllipseArc(ellipse1, ellipseArc2)
      for line in lines:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(line.getStartPt()):
            result.append(line)
      return result


   # ===============================================================================
   # methods for ellipse arcs - end
   # methods for basic geometric objects - start
   # ===============================================================================


   # ============================================================================
   # fromPointToBasicGeomObject
   # ============================================================================
   @staticmethod
   def fromPointToBasicGeomObject(pt, object):
      """the function returns a list of points of tangency on the object passing through a point
            the function returns the points of tangency on a basic geometric object:
            line, arc, ellipse arc, circle, ellipse.
      """
      if object.whatIs() == "CIRCLE":
         return QadTangency.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         return QadTangency.fromPointToArc(pt, object)
      elif object.whatIs() == "ELLIPSE":
         return QadTangency.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         return QadTangency.fromPointToEllipseArc(pt, object)

      return []


   # ============================================================================
   # fromPointToBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def fromPointToBasicGeomObjectExtensions(pt, object):
      """the function returns a list of tangency points on an extension of a basic geometric object passing through a point
            arc (becomes circle), arc of ellipse (becomes ellipse), circle, ellipse.
      """
      if object.whatIs() == "CIRCLE":
         return QadTangency.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object.center, object.radius)
         return QadTangency.fromPointToCircle(pt, circle)
      elif object.whatIs() == "ELLIPSE":
         return QadTangency.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object.center, object.majorAxisFinalPt, object.axisRatio)
         return QadTangency.fromPointToEllipse(pt, ellipse)

      return []


   # ============================================================================
   # fromPointToGeomObject
   # ============================================================================
   @staticmethod
   def fromPointToGeomObject(pt, object):
      """the function returns a list of points of tangency on the object passing through a point"""
      geomType = object.whatIs()
      result = []

      if geomType == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadTangency.fromPointToBasicGeomObject(pt, linearObj))

      elif geomType == "POLYLINE":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadTangency.fromPointToBasicGeomObject(pt, linearObj))

      elif geomType == "POLYGON":
         for subGeomAt in range(0, object.qty()):
            closedObj = object.getClosedObjectAt(geomAt)
            result.extend(QadTangency.fromPointToGeomObject(pt, closedObj))

      elif geomType == "MULTI_POLYGON":
         for geomAt in range(0, object.qty()):
            polygon = object.getPolygonAt(geomAt)
            result.extend(QadTangency.fromPointToGeomObject(pt, polygon))

      # object is a basic geometry
      else:
         result.extend(QadTangency.fromPointToBasicGeomObject(pt, object))

      return result


   # ============================================================================
   # bestTwoBasicGeomObjects
   # ============================================================================
   @staticmethod
   def bestTwoBasicGeomObjects(object1, tanPt1, object2, tanPt2):
      """Find the line tangent to one basic geometric object and tangent to another basic geometric object
            (which has the starting/ending points that are respectively closest to the tanPt1 and tanPt2 points):
            arc, ellipse arc, circle, ellipse.
            tanPt1 = geometry selection point 1 of tangency
            tanPt2 = geometry selection point 2 of tangency
      """
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromCircleToArc(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromCircleToEllipse(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromCircleToEllipseArc(object1, object2), tanPt1, tanPt2)

      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.fromCircleToArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoArcs(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromArcToEllipse(object1, sobject2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromArcToEllipseArc(object1, object2), tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.fromCircleToEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            lines = QadTangency.fromArcToEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipses(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromEllipseToEllipseArc(object1, object2), tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.fromCircleToEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            lines = QadTangency.fromArcToEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            lines = QadTangency.fromEllipseToEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipseArcs(object1, object2), tanPt1, tanPt2)

      return None


   # ============================================================================
   # bestTwoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def bestTwoBasicGeomObjectExtensions(object1, tanPt1, object2, tanPt2):
      """Finds the line tangent to the extent of a basic geometric object and tangent to an extent
            of another basic geometric object (which has the starting/ending points which are respectively
            closest to the points tanPt1 and tanPt2):
            arc, ellipse arc, circle, ellipse.
            tanPt1 = geometry selection point 1 of tangency
            tanPt2 = geometry selection point 2 of tangency
      """
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(object1, circle2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(object1, ellipse2), tanPt1, tanPt2)

      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         if object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(circle1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(circle1, circle2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(circle1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(circle1, ellipse2), tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.circleWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadTangency.circleWithEllipse(circle2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipses(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            lines = QadTangency.ellipseWithEllipseArc(object1, ellipse2)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.circleWithEllipse(object2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadTangency.circleWithEllipse(circle2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipses(ellipse1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipseArcs(ellipse1, ellipse2), tanPt1, tanPt2)

      return None


# ===============================================================================
# QadTangPerp class
# represents a class that calculates lines tangent to one object and perpendicular to another object
# ===============================================================================
class QadTangPerp():

   def __init__(self):
      pass


   # ===============================================================================
   # methods for circles - start
   # ===============================================================================


   # ===============================================================================
   # circleWithInfinityLine
   # ===============================================================================
   @staticmethod
   def circleWithInfinityLine(circle1, line2):
      """Find the lines tangent to a circle and perpendicular to an infinite line"""
      lines = []
      # lines tangent to a circle and perpendicular to a line
      angle = line2.getTanDirectionOnStartPt()
      pt1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
      pt2 = QadPerpendicularity.fromPointToInfinityLine(pt1, line2)
      if pt2 is not None:
         line = QadLine()
         line.set(pt1, pt2) # first tangent point and second perpendicular point
         lines.append(line)

      pt1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, -1 * circle1.radius)
      pt2 = QadPerpendicularity.fromPointToInfinityLine(pt1, line2)
      if pt2 is not None:
         line = QadLine()
         line.set(pt1, pt2) # first tangent point and second perpendicular point
         lines.append(line)

      return lines


   # ===============================================================================
   # circleWithLine
   # ===============================================================================
   @staticmethod
   def circleWithLine(circle1, line2):
      """Find lines tangent to a circle and perpendicular to a line"""
      lines = QadTangPerp.circleWithInfinityLine(circle1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """Find lines tangent to one circle and perpendicular to another circle"""
      lines = []
      points = QadTangency.fromPointToCircle(circle2.center, circle1)
      for point in points:
         angle = qad_utils.getAngleBy2Pts(circle2.center, point)
         pt1 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, circle2.radius)
         line = QadLine()
         line.set(point, pt1) # first tangent point and second perpendicular point
         lines.append(line)
         pt1 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, -1 * circle2.radius)
         line = QadLine()
         line.set(point, pt1) # first tangent point and second perpendicular point
         lines.append(line)

      return lines


   # ===============================================================================
   # circleWithArc
   # ===============================================================================
   @staticmethod
   def circleWithArc(circle1, arc2):
      """Find the lines tangent to a circle and perpendicular to an arc"""
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)

      lines = QadTangPerp.twoCircles(circle1, circle2)

      if len(lines) == 2:
         if arc2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # circleWithEllipse
   # ===============================================================================
   @staticmethod
   def circleWithEllipse(circle1, ellipse2):
      """Find lines tangent to a circle and perpendicular to an ellipse"""
      # TODO
      return []


   # ===============================================================================
   # circleWithEllipseArc
   # ===============================================================================
   @staticmethod
   def circleWithEllipseArc(circle1, ellipseArc2):
      """Find lines tangent to a circle and perpendicular to an arc of an ellipse"""
      # TODO
      return []


   # ===============================================================================
   # methods for circles - end
   # methods for arcs - start
   # ===============================================================================


   # ===============================================================================
   # arcWithInfinityLine
   # ===============================================================================
   @staticmethod
   def arcWithInfinityLine(arc1, line2):
      """Find the lines tangent to an arc and perpendicular to an infinite line"""
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)

      lines = QadTangPerp.circleWithInfinityLine(circle1, line2)

      if len(lines) == 2:
         if arc1.containsPt(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.containsPt(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # arcWithLine
   # ===============================================================================
   @staticmethod
   def arcWithLine(arc1, line2):
      """Find lines tangent to an arc and perpendicular to a line"""
      lines = QadTangPerp.arcWithInfinityLines(arc1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # arcWithCircle
   # ===============================================================================
   @staticmethod
   def arcWithCircle(arc1, circle2):
      """Find lines tangent to an arc and perpendicular to a circle"""
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)

      lines = QadTangPerp.twoCircles(circle1, circle2)

      if len(lines) == 2:
         if arc1.containsPt(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.containsPt(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # twoArcs
   # ===============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """Find lines tangent to one arc and perpendicular to another arc"""
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)

      lines = QadTangPerp.arcWithCircle(arc1, circle2)

      if len(lines) == 2:
         if arc2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # arcWithEllipse
   # ===============================================================================
   @staticmethod
   def arcWithEllipse(arc1, ellipse2):
      """Find lines tangent to an arc and perpendicular to an ellipse"""
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)

      lines = QadTangPerp.circleWithEllipse(circle1, ellipse2)

      if len(lines) == 2:
         if arc1.containsPt(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.containsPt(lines[0].getStartPt()) == False: del(lines[1])

      return lines


   # ===============================================================================
   # arcWithEllipseArc
   # ===============================================================================
   @staticmethod
   def arcWithEllipseArc(arc1, ellipseArc2):
      """Find lines tangent to an arc and perpendicular to an arc of ellipse"""
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)

      lines = QadTangPerp.arcWithEllipse(arc1, ellipse2)

      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # methods for arcs - end
   # methods for ellipses - start
   # ===============================================================================


   # ===============================================================================
   # ellipseWithInfinityLine
   # ===============================================================================
   @staticmethod
   def ellipseWithInfinityLine(ellipse1, line2):
      """Find lines tangent to an ellipse and perpendicular to an infinite line"""
      # TODO
      return []


   # ===============================================================================
   # ellipseWithLine
   # ===============================================================================
   @staticmethod
   def ellipseWithLine(ellipse1, line2):
      """Find lines tangent to an ellipse and perpendicular to a line"""
      lines = QadTangPerp.ellipseWithInfinityLines(ellipse1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseWithCircle
   # ===============================================================================
   @staticmethod
   def ellipseWithCircle(ellipse1, circle2):
      """Find lines tangent to an ellipse and perpendicular to a circle"""
      # TODO
      return []


   # ===============================================================================
   # ellipseWithArc
   # ===============================================================================
   @staticmethod
   def ellipseWithArc(ellipse1, arc2):
      """Find lines tangent to an ellipse and perpendicular to an arc"""
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)

      lines = QadTangPerp.ellipseWithCircle(ellipse1, tanPt1, circle2, perPt2)

      if len(lines) == 2:
         if arc2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # twoEllipses
   # ===============================================================================
   @staticmethod
   def twoEllipses(ellipse1, ellipse2):
      """Find lines tangent to one ellipse and perpendicular to another ellipse"""
      # TODO
      return []


   # ===============================================================================
   # ellipseWithEllipseArc
   # ===============================================================================
   @staticmethod
   def ellipseWithEllipseArc(ellipse1, ellipseArc2):
      """Find lines tangent to an ellipse and perpendicular to an arc of an ellipse"""
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)

      lines = QadTangPerp.twoEllipses(ellipse1, ellipse2)

      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # methods for ellipses - end
   # methods for ellipse arcs - start
   # ===============================================================================


   # ===============================================================================
   # ellipseArcWithInfinityLine
   # ===============================================================================
   @staticmethod
   def ellipseArcWithInfinityLine(ellipseArc1, line2):
      """Find lines tangent to an arc of ellipse and perpendicular to an infinite line"""
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)

      lines = QadTangPerp.ellipseWithInfinityLine(ellipse1, line2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithLine
   # ===============================================================================
   @staticmethod
   def ellipseArcWithLine(ellipseArc1, line2):
      """Find lines tangent to an arc of ellipse and perpendicular to a line"""
      lines = QadTangPerp.ellipseArcWithInfinityLine(ellipseArc1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithCircle
   # ===============================================================================
   @staticmethod
   def ellipseArcWithCircle(ellipseArc1, circle2):
      """Find lines tangent to an arc of an ellipse and perpendicular to a circle"""
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)

      lines = QadTangPerp.ellipseWithCircle(ellipse1, line2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithArc
   # ===============================================================================
   @staticmethod
   def ellipseArcWithArc(ellipseArc1, arc2):
      """Find lines tangent to an arc of ellipse and perpendicular to an arc"""
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)

      lines = QadTangPerp.ellipseWithArc(ellipse1, arc2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithEllipse
   # ===============================================================================
   @staticmethod
   def ellipseArcWithEllipse(ellipseArc1, ellipse2):
      """Find lines tangent to an arc of ellipse and perpendicular to an ellipse"""
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)

      lines = QadTangPerp.twoEllipses(ellipse1, ellipse2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # twoEllipseArcs
   # ===============================================================================
   @staticmethod
   def twoEllipseArcs(ellipseArc1, ellipseArc2):
      """Find lines tangent to one arc of ellipse and perpendicular to another arc of ellipse"""
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)

      lines = QadTangPerp.ellipseWithEllipseArc(ellipse1, ellipseArc2)

      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ============================================================================
   # bestTwoBasicGeomObjects
   # ============================================================================
   @staticmethod
   def bestTwoBasicGeomObjects(object1, tanPt1, object2, perPt2):
      """Find the line tangent to one basic geometric object and perpendicular to another basic geometric object
            (which has the starting/ending points that are respectively closest to the points tanPt1 and perPt2):
            line, arc, ellipse arc, circle, ellipse.
            tanPt1 = tangency geometry selection point
            perPt2 = perpendicularity geometry selection point
      """
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoCircles(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithArc(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipseArc(object1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoArcs(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithEllipseArc(object1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithArc(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithEllipseArc(object1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithArc(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipseArcs(object1, object2), tanPt1, perPt2)

      return None


   # ============================================================================
   # bestTwoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def bestTwoBasicGeomObjectExtensions(object1, tanPt1, object2, perPt2):
      """Finds lines tangent to the extent of a basic geometric object and perpendicular to an extent
            of another basic geometric object (which has the starting/ending points that respectively
            are closest to the points tanPt1 and perPt2):
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
            tanPt1 = tangency geometry selection point
            perPt2 = perpendicularity geometry selection point
      """
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithInfinityLine(object2, object1), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoCircles(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoCircles(object1, circle), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipse(object1, ellipse), tanPt1, perPt2)

      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         return getLineWithStartEndPtsClosestToPts(QadTangPerp.fromTwoBasicGeomObjectExtensions(circle1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithInfinityLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(object1, circle), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(object1, ellipse), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithInfinityLine(ellipse1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(ellipse1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object.center, object.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(ellipse1, circle), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(ellipse1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(ellipse1, ellipse2), tanPt1, perPt2)

      return None


# ===============================================================================
# QadPerpPerp class
# represents a class that calculates lines perpendicular to one object and perpendicular to another object
# ===============================================================================
class QadPerpPerp():

   def __init__(self):
      pass


   # ===============================================================================
   # methods for infinite lines - start
   # ===============================================================================


   # ===============================================================================
   # infinityLineWithCircle
   # ===============================================================================
   @staticmethod
   def infinityLineWithCircle(infinityLine1, circle2):
      """The function returns the perpendicular line between line1 considered an infinite line and a circle."""
      # line perpendicular to a line and a circle
      ptPer1 = QadPerpendicularity.fromPointToInfinityLine(circle2.center, infinityLine1)
      angle = qad_utils.getAngleBy2Pts(circle2.center, ptPer1)
      ptPer2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, circle2.radius)
      line = QadLine()
      line.set(ptPer1, ptPer2)
      return line


   # ===============================================================================
   # infinityLineWithArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithArc(infinityLine1, arc2):
      """The function returns the line perpendicular to line1 considered an infinite line and an arc."""
      circle = QadCircle()
      circle.set(arc2.center, arc2.radius)
      line = QadPerpPerp.infinityLineWithCircle(infinityLine1, circle)
      if line is None: return None
      if arc2.isPtOnArcOnlyByAngle(line.getEndPt()): return line
      return None


   # ===============================================================================
   # infinityLineWithEllipse
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipse(infinityLine1, ellipse2):
      """The function returns the lines perpendicular to line1 considered infinite line and an ellipse.
            (up to 4 lines)
      """
      # TODO
      return []


   # ===============================================================================
   # infinityLineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipseArc(infinityLine1, ellipseArc2):
      """The function returns the lines perpendicular to line 1 considered infinite line and an arc of ellipse.
            (up to 4 lines)
      """
      ellipse = QadEllipse()
      ellipse.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadPerpPerp.infinityLineWithEllipse(infinityLine1, ellipse)

      if len(lines) == 4:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[3].getEndPt()) == False: del(lines[3])
      if len(lines) == 3:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[2].getEndPt()) == False: del(lines[2])
      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])
      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # methods for infinite lines - end
   # segment methods - start
   # ===============================================================================

   # ===============================================================================
   # lineWithLine
   # ===============================================================================
   @staticmethod
   def lineWithLine(line1, perPt1, line2, perPt2):
      """The function returns the line perpendicular to a segment to a segment."""
      ang1 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt()), math.pi)
      ang2 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt()), math.pi)
      if qad_utils.TanDirectionNear(ang1, ang2) == True:
         result = QadLine()
         result.set(perPt1, perPt2)
         return result

      return None

   # ===============================================================================
   # lineWithCircle
   # ===============================================================================
   @staticmethod
   def lineWithCircle(line1, circle2):
      """The function returns the line perpendicular to a segment and a circle."""
      line = QadPerpPerp.infinityLineWithCircle(line1, circle2)
      if line is None: return None
      if line1.containsPt(line.getStartPt()): return line
      return None


   # ===============================================================================
   # lineWithArc
   # ===============================================================================
   @staticmethod
   def lineWithArc(line1, arc2):
      """The function returns the line perpendicular to a segment and an arc."""
      circle = QadCircle()
      circle.set(arc2.center, arc2.radius)
      line = QadPerpPerp.lineWithCircle(line1, circle)
      if line is None: return None
      if arc2.isPtOnArcOnlyByAngle(line.getEndPt()): return line
      return None


   # ===============================================================================
   # lineWithEllipse
   # ===============================================================================
   @staticmethod
   def lineWithEllipse(line1, ellipse2):
      """The function returns lines perpendicular to a segment and an ellipse.
            (up to 4 lines)
      """
      lines = QadPerpPerp.infinityLineWithEllipse(line1, ellipse2)

      if len(lines) == 4:
         if line1.containsPt(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if line1.containsPt(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if line1.containsPt(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if line1.containsPt(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # lineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def lineWithEllipseArc(line1, ellipseArc2):
      """The function returns lines perpendicular to a segment and an arc of an ellipse.
            (up to 4 lines)
      """
      lines = QadPerpPerp.infinityLineWithEllipseArc(line1, ellipseArc)

      if len(lines) == 4:
         if line1.containsPt(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if line1.containsPt(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if line1.containsPt(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if line1.containsPt(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # segment methods - end
   # methods for circles - start
   # ===============================================================================


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """The function returns the perpendicular line between two circles"""
      angle = qad_utils.getAngleBy2Pts(circle1.center, circle2.center)
      ptPer1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
      ptPer2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, -circle2.radius)
      line = QadLine()
      line.set(ptPer1, ptPer2)
      return line


   # ===============================================================================
   # circleWithArc
   # ===============================================================================
   @staticmethod
   def circleWithArc(circle1, arc2):
      """The function returns the line perpendicular to a circle and an arc"""
      circle = QadCircle()
      circle.set(arc2.center, arc2.radius)
      line = QadPerpPerp.twoCircles(circle1, circle)
      if line is None: return None
      if arc2.isPtOnArcOnlyByAngle(line.getEndPt()): return line
      return None


   # ===============================================================================
   # circleWithEllipse
   # ===============================================================================
   @staticmethod
   def circleWithEllipse(circle1, ellipse2):
      """The function returns the perpendicular lines between a circle and an ellipse
            (up to 4 lines)
      """
      perpPts = QadPerpendicularity.fromPointToEllipse(circle1.center, ellipse2)
      lines = []
      for perpPt2 in perpPts:
         angle = qad_utils.getAngleBy2Pts(circle1.center, perpPt2)
         perPt1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
         line = QadLine()
         line.set(perPt1, perpPt2)
         lines.append(line)
      return lines


   # ===============================================================================
   # circleWithEllipseArc
   # ===============================================================================
   @staticmethod
   def circleWithEllipseArc(circle1, ellipseArc2):
      """The function returns lines perpendicular to a circle and an ellipse
            (up to 4 lines)
      """
      ellipse = QadEllipse()
      ellipse.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadPerpPerp.circleWithEllipse(circle1, ellipse)

      if len(lines) == 4:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[3].getEndPt()) == False: del(lines[3])
      if len(lines) == 3:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[2].getEndPt()) == False: del(lines[2])
      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])
      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # methods for circles - end
   # methods for arcs - start
   # ===============================================================================


   # ===============================================================================
   # twoArcs
   # ===============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """The function returns lines perpendicular to two arcs"""
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      line = QadPerpPerp.circleWithArc(circle1, arc2)
      if line is None: return None
      if arc1.isPtOnArcOnlyByAngle(line.getStartPt()): return line
      return None


   # ===============================================================================
   # arcWithEllipse
   # ===============================================================================
   @staticmethod
   def arcWithEllipse(arc1, ellipse2):
      """The function returns lines perpendicular to an arc and an ellipse
            (up to 4 lines)
      """
      circle = QadCircle()
      circle.set(arc1.center, arc1.radius)
      lines = QadPerpPerp.circleWithEllipse(circle, ellipse2)

      if len(lines) == 4:
         if arc1.isPtOnArcOnlyByAngle(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if arc1.isPtOnArcOnlyByAngle(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if arc1.isPtOnArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if arc1.isPtOnArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # arcWithEllipseArc
   # ===============================================================================
   @staticmethod
   def arcWithEllipseArc(arc1, ellipseArc2):
      """The function returns lines perpendicular to an arc and an arc of an ellipse
            (up to 4 lines)
      """
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadPerpPerp.circleWithEllipseArc(circle1, ellipseArc2)

      if len(lines) == 4:
         if arc1.isPtOnArcOnlyByAngle(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if arc1.isPtOnArcOnlyByAngle(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if arc1.isPtOnArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if arc1.isPtOnArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # methods for arcs - end
   # ===============================================================================


   # ============================================================================
   # bestTwoBasicGeomObjects
   # ============================================================================
   @staticmethod
   def bestTwoBasicGeomObjects(object1, perPt1, object2, perPt2):
      """Find the line perpendicular to one basic geometric object and perpendicular to another basic geometric object
            (which has the starting/ending points that are respectively closest to the points tanPt1 and perPt2):
            line, arc, ellipse arc, circle, ellipse.
            perPt1 = geometry selection point 1 of perpendicularity
            perPt2 = geometry selection point 2 of perpendicularity
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            return QadPerpPerp.lineWithLine(object1, perPt1, object2, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.lineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            result = QadPerpPerp.lineWithArc(object1, object2)
            if result is not None:
               pts = QadIntersections.infinityLineWithArc(result, object2)
               if len(pts) == 2:
                  if qad_utils.getDistance(perPt2, pts[0]) <= qad_utils.getDistance(perPt2, pts[1]):
                     result.setEndPt(pts[0])
                  else:
                     result.setEndPt(pts[1])
            return result
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.lineWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.lineWithEllipseArc(object1, object2), perPt1, perPt2)

      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.lineWithCircle(object2, object1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadPerpPerp.circleWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipseArc(object1, object2), perPt1, perPt2)

      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.lineWithArc(object2, object1)
            if result is not None:
               pts = QadIntersections.infinityLineWithArc(result, object1)
               if len(pts) == 2:
                  if qad_utils.getDistance(perPt1, pts[0]) <= qad_utils.getDistance(perPt1, pts[1]):
                     result.setEndPt(pts[0])
                  else:
                     result.setEndPt(pts[1])

            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            result = QadPerpPerp.lineWithCircle(object2, object1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "ARC":
            return QadPerpPerp.twoArcs(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.arcWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.arcWithEllipseArc(object1, object2), perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.lineWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            lines = QadPerpPerp.circleWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            lines = QadPerpPerp.arcWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.lineWithEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            QadPerpPerp.circleWithEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            lines = QadPerpPerp.arcWithEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)

      return None


   # ============================================================================
   # bestTwoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod
   def bestTwoBasicGeomObjectExtensions(object1, tanPt1, object2, perPt2):
      """Finds the line perpendicular to the extent of a basic geometric object and perpendicular to an extent
            of another basic geometric object (which has the starting/ending points which are respectively
            closest to the points perPt1 and perPt2):
            line (becomes infinite line), arc (becomes circle), ellipse arc (becomes ellipse), circle, ellipse.
            perPt1 = geometry selection point 1 of perpendicularity
            perPt2 = geometry selection point 2 of perpendicularity
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "CIRCLE":
            return QadPerpPerp.infinityLineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadPerpPerp.infinityLineWithCircle(object1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.infinityLineWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.infinityLineWithEllipse(object1, ellipse2), perPt1, perPt2)

      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.infinityLineWithCircle(object2, object1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadPerpPerp.twoCircles(object1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(object1, ellipse2), perPt1, perPt2)

      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.infinityLineWithCircle(object2, circle1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.twoCircles(circle1, object2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadPerpPerp.twoCircles(circle1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(circle1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(circle1, ellipse2), perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.infinityLineWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            lines = QadPerpPerp.circleWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadPerpPerp.circleWithEllipse(circle2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.infinityLineWithEllipse(object2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            QadPerpPerp.circleWithEllipse(object2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadPerpPerp.circleWithEllipse(circle2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)

      return None


# ===============================================================================
# getLineWithStartEndPtsClosestToPts
# ===============================================================================
def getLineWithStartEndPtsClosestToPts(lines, pt1, pt2):
   """Given a list of lines, it returns the line that has the initial and final point respectively
      closest to pt1 and pt2 (the function uses the average of the distances).
   """
   if len(lines) == 0:
      return None

   Avg = sys.float_info.max
   for line in lines:
      d1 = qad_utils.getDistance(line.getStartPt(), pt1)
      d2 = qad_utils.getDistance(line.getEndPt(), pt2)
      currAvg = (d1 + d2) / 2.0
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result = line

   return result


# ===============================================================================
# getQadGeomClosestPart
# ===============================================================================
def getQadGeomClosestPart(qadGeom, pt):
   """the function returns a list with
      (<minimum distance>
       <nearest point>
       <nearest geometry index>
       <index of the closest sub-geometry>
       <index of the closest sub-geometry part>
       <"to the left of" if the point is to the left of the part with the following values:
       - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
       - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
       )
   """
   geomType = qadGeom.whatIs()
   if geomType == "POINT" or geomType == "LINE" or geomType == "ARC" or \
      geomType == "CIRCLE" or geomType == "ELLIPSE_ARC" or geomType == "ELLIPSE":
      # the function returns a list with (<minimum distance><minimum distance point>)
      result = QadMinDistance.fromPointToBasicGeomObject(pt, qadGeom)
      dist = result[0]
      minDistPoint = result[1]

      if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
         # < 0 "to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
         leftOf = qadGeom.leftOf(pt)
      elif geomType == "CIRCLE" or geomType == "ELLIPSE_ARC" or geomType == "ELLIPSE": # circle or ellipse
         leftOf = qadGeom.whereIsPt(pt) # -1 inside, 0 sulla circonferenza, 1 outside
      else:
         leftOf = None

      return (dist, minDistPoint, 0, 0, 0, leftOf)

   elif qadGeom.whatIs() == "POLYLINE":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = i
            leftOf = result[5]
         i = i + 1

      return (dist, minDistPoint, 0, 0, partIndex, leftOf)

   elif qadGeom.whatIs() == "POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getClosedObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = result[4]
            leftOf = result[5]
            subGeomIndex = i
         i = i + 1

      return (dist, minDistPoint, 0, subGeomIndex, partIndex, leftOf)

   elif qadGeom.whatIs() == "MULTI_POINT":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getPointAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
         i = i + 1

      return (dist, minDistPoint, geomIndex, 0, 0, None)

   elif qadGeom.whatIs() == "MULTI_LINEAR_OBJ":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            partIndex = result[4]
            leftOf = result[5]
         i = i + 1

      return (dist, minDistPoint, geomIndex, 0, partIndex, leftOf)

   elif qadGeom.whatIs() == "MULTI_POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getPolygonAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            subGeomIndex = result[3]
            partIndex = result[4]
            leftOf = result[5]
         i = i + 1

      return (dist, minDistPoint, geomIndex, subGeomIndex, partIndex, leftOf)

   else:
      return (None, None, None, None, None, None)


# ===============================================================================
# getQadGeomClosestVertex
# ===============================================================================
def getQadGeomClosestVertex(qadGeom, pt):
   """the function returns a list with
      (<minimum distance>
       <nearest vertex point>
       <nearest geometry index>
       <index of the closest sub-geometry>
       <index of the closest sub-geometry part>
       <nearest vertex index>
       )
   """
   geomType = qadGeom.whatIs()
   if geomType == "POINT":
      return (qad_utils.getDistance(qadGeom, pt), qadGeom, 0, 0, 0, 0)

   elif geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
      startPt = qadGeom.getStartPt()
      endPt = qadGeom.getEndPt()
      d1 = qad_utils.getDistance(startPt, pt)
      d2 = qad_utils.getDistance(endPt, pt)
      if d1 < d2:
         return (d1, startPt, 0, 0, 0, 0)
      else:
         return (d2, endPt, 0, 0, 0, 1)

   elif qadGeom.whatIs() == "POLYLINE":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = i
            vertexIndex = partIndex + result[5]
         i = i + 1

      return (dist, minDistPoint, 0, 0, partIndex, vertexIndex)

   elif qadGeom.whatIs() == "POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getClosedObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = result[4]
            vertexIndex = result[5]
            subGeomIndex = i
         i = i + 1

      return (dist, minDistPoint, 0, subGeomIndex, partIndex, vertexIndex)

   elif qadGeom.whatIs() == "MULTI_POINT":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getPointAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
         i = i + 1

      return (dist, minDistPoint, geomIndex, 0, 0, 0)

   elif qadGeom.whatIs() == "MULTI_LINEAR_OBJ":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            partIndex = result[4]
            vertexIndex = result[5]
         i = i + 1

      return (dist, minDistPoint, geomIndex, 0, partIndex, vertexIndex)

   elif qadGeom.whatIs() == "MULTI_POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getPolygonAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            subGeomIndex = result[3]
            partIndex = result[4]
            vertexIndex = result[5]
         i = i + 1

      return (dist, minDistPoint, geomIndex, subGeomIndex, partIndex, vertexIndex)

   else:
      # the function returns a list with (<minimum distance><minimum distance point>)
      result = QadMinDistance.fromPointToBasicGeomObject(pt, qadGeom)
      dist = result[0]
      minDistPoint = result[1]

      return (dist, minDistPoint, 0, 0, None, None)


# ===============================================================================
# getGeomBetween2Pts
# ===============================================================================
def getQadGeomBetween2Pts(qadGeom, startPt, endPt):
   """Returns a sub-geometry that starts from the startPt point and ends at the endPt point following the geometry path."""
   # the function returns a list with
   # (<minimum distance>
   # <nearest point>
   # <nearest geometry index>
   # <index of the nearest sub-geometry>
   # if closed geometry is polyline type the list also contains
   # <index of the closest sub-geometry part>
   # <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
   dummy = getQadGeomClosestPart(qadGeom, startPt)
   ptEnd = dummy[1]
   # returns the sub-geometry
   g = getQadGeomAt(qadGeom, dummy[2], dummy[3])

   geomType = g.whatIs()
   if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
      return g.getGeomBetween2Pts(startPt, endPt)

   elif qadGeom.whatIs() == "POLYLINE":
      return g.getGeomBetween2Pts(startPt, endPt)

   elif qadGeom.whatIs() == "CIRCLE":
      angle1 = qad_utils.getAngleBy2Pts(g.center, startPt)
      angle2 = qad_utils.getAngleBy2Pts(g.center, endPt)

      arc1 = QadArc()
      arc1.set(g.center, g.radius, angle1, angle2)
      arc2 = QadArc()
      arc2.set(g.center, g.radius, angle2, angle1)

      if arc1.length() < arc2.length():
         if qad_utils.ptNear(arc1.getStartPt(), startPt) == False: arc1.reversed = True
         return arc1
      else:
         if qad_utils.ptNear(arc2.getStartPt(), startPt) == False: arc2.reversed = True
         return arc2

   elif qadGeom.whatIs() == "ELLIPSE":
      angle1 = qad_utils.getAngleBy2Pts(g.center, startPt)
      angle2 = qad_utils.getAngleBy2Pts(g.center, endPt)

      arc1 = QadEllipseArc()
      arc1.set(g.center, g.majorAxisFinalPt, g.axisRatio, angle1, angle2)
      arc2 = QadEllipseArc()
      arc2.set(g.center, g.majorAxisFinalPt, g.axisRatio, angle2, angle1)

      if arc1.length() < arc2.length():
         if qad_utils.ptNear(arc1.getStartPt(), startPt) == False: arc1.reversed = True
         return arc1
      else:
         if qad_utils.ptNear(arc2.getStartPt(), startPt) == False: arc2.reversed = True
         return arc2


# ===============================================================================
# appendPtOnTheSameTanDirectionOnly
# ===============================================================================
def appendPtOnTheSameTanDirectionOnly(line, pts, resultList):
   """Adds points from the pts list only if they are in the same direction as the tangent of the line.
      It is used, for example, to add the intersection points on the extension of the first and last line of a polyline.
   """
   angle = line.getTanDirectionOnPt()
   for pt in pts:
      if qad_utils.ptNear(pt, line.pt1) or \
         qad_utils.doubleNear(angle, qad_utils.getAngleBy2Pts(line.pt1, pt)):
         resultList.append(pt)



