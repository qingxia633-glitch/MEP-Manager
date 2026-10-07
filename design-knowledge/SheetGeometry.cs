using System;
namespace MepSheet {
 public static class Geometry {
  static double[] Cross(double[] a,double[] b){return new[]{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
  static double[] Unit(double[] a){double d=Math.Sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]);if(d<1e-12)throw new ArgumentException("Invalid normal");return new[]{a[0]/d,a[1]/d,a[2]/d};}
  // INSERT DXF10 is OCS. Block base point is subtracted before scale and rotation.
  public static double[] Transform(double[] p,double[] basis,double[] insertion,double[] scale,double angle,double[] normal){
   if(p.Length!=3||basis.Length!=3||insertion.Length!=3||scale.Length!=3||normal.Length!=3)throw new ArgumentException("Incomplete transform");
   if(Array.Exists(scale,value=>Math.Abs(value)<1e-12))throw new ArgumentException("Singular scale");
   var z=Unit(normal);var x=Unit(Cross(Math.Abs(z[0])<1.0/64&&Math.Abs(z[1])<1.0/64?new[]{0.0,1.0,0.0}:new[]{0.0,0.0,1.0},z));var y=Cross(z,x);
   double a=(p[0]-basis[0])*scale[0],b=(p[1]-basis[1])*scale[1];
   double u=a*Math.Cos(angle)-b*Math.Sin(angle)+insertion[0],v=a*Math.Sin(angle)+b*Math.Cos(angle)+insertion[1],w=(p[2]-basis[2])*scale[2]+insertion[2];
   return new[]{x[0]*u+y[0]*v+z[0]*w,x[1]*u+y[1]*v+z[1]*w,x[2]*u+y[2]*v+z[2]*w};
  }
  public static double[] Bounds(double[][] p){double[] b={double.PositiveInfinity,double.PositiveInfinity,double.NegativeInfinity,double.NegativeInfinity};foreach(var q in p){b[0]=Math.Min(b[0],q[0]);b[1]=Math.Min(b[1],q[1]);b[2]=Math.Max(b[2],q[0]);b[3]=Math.Max(b[3],q[1]);}return b;}
  public static double[][] Box(double[] b){return new[]{new[]{b[0],b[1],0.0},new[]{b[2],b[1],0.0},new[]{b[2],b[3],0.0},new[]{b[0],b[3],0.0}};}
  public static double Area(double[][] p){double a=0;for(int i=0;i<p.Length;i++){var q=p[(i+1)%p.Length];a+=p[i][0]*q[1]-q[0]*p[i][1];}return Math.Abs(a/2);}
  // Convex polygons only; explicit validation before using containment.
  public static bool Valid(double[][] p,double tol){if(p.Length<3||Area(p)<=tol*tol)return false;double sign=0;for(int i=0;i<p.Length;i++){var a=p[i];var b=p[(i+1)%p.Length];var c=p[(i+2)%p.Length];if(Math.Abs(a[2]-p[0][2])>tol)return false;double k=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]);if(Math.Abs(k)<=tol*tol)continue;if(sign*k<0)return false;sign=k;}return true;}
  public static int Point(double[][] p,double[] q,double tol){bool inside=false;for(int i=0,j=p.Length-1;i<p.Length;j=i++) {var a=p[j];var b=p[i];double dx=b[0]-a[0],dy=b[1]-a[1],l=dx*dx+dy*dy;if(l>0){double t=Math.Max(0,Math.Min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/l));if(Math.Sqrt(Math.Pow(q[0]-a[0]-t*dx,2)+Math.Pow(q[1]-a[1]-t*dy,2))<=tol)return 0;}if((a[1]>q[1])!=(b[1]>q[1])&&q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;}return inside?1:-1;}
  public static bool Intersects(double[][] a,double[][] b,double tol){foreach(var poly in new[]{a,b})for(int i=0;i<poly.Length;i++){var p=poly[i];var q=poly[(i+1)%poly.Length];double nx=-(q[1]-p[1]),ny=q[0]-p[0],len=Math.Sqrt(nx*nx+ny*ny);if(len<=tol)continue;nx/=len;ny/=len;double amin=double.PositiveInfinity,amax=double.NegativeInfinity,bmin=amin,bmax=amax;foreach(var v in a){double d=(v[0]-p[0])*nx+(v[1]-p[1])*ny;amin=Math.Min(amin,d);amax=Math.Max(amax,d);}foreach(var v in b){double d=(v[0]-p[0])*nx+(v[1]-p[1])*ny;bmin=Math.Min(bmin,d);bmax=Math.Max(bmax,d);}if(amax<bmin-tol||bmax<amin-tol)return false;}return true;}
  public static string Relation(double[][] frame,double[][] region,double tol){if(!Intersects(frame,region,tol))return "outside";bool all=true;foreach(var p in region)if(Point(frame,p,tol)!=1)all=false;return all?"inside":"boundary";}
 }
}
