using System;
namespace Mep.Spatial {
 public static class Polygon {
  static double Cross(double[] a,double[] b,double[] c){return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
  static double Distance(double[] a,double[] b){double x=a[0]-b[0],y=a[1]-b[1],z=a[2]-b[2];return Math.Sqrt(x*x+y*y+z*z);}
  static bool Finite(double[] p){return p!=null&&p.Length==3&&!Array.Exists(p,x=>Double.IsNaN(x)||Double.IsInfinity(x));}
  public static double SegmentDistance(double[] p,double[] a,double[] b){
   double x=b[0]-a[0],y=b[1]-a[1],z=b[2]-a[2],den=x*x+y*y+z*z;
   if(den==0)return Distance(p,a);
   double t=Math.Max(0,Math.Min(1,((p[0]-a[0])*x+(p[1]-a[1])*y+(p[2]-a[2])*z)/den));
   return Distance(p,new[]{a[0]+t*x,a[1]+t*y,a[2]+t*z});
  }
  public static bool Valid(double[][] v,double tol){
   if(v==null||v.Length<3||Array.Exists(v,p=>!Finite(p)))return false;
   double area=0;
   for(int i=0;i<v.Length;i++){
    var a=v[i];var b=v[(i+1)%v.Length];
    if(Math.Abs(a[2]-v[0][2])>tol||Distance(a,b)<=tol)return false;
    area+=Cross(v[0],a,b);
    for(int j=i+1;j<v.Length;j++){
     if(j==i+1||(i==0&&j==v.Length-1))continue;
     var c=v[j];var d=v[(j+1)%v.Length];
     if(SegmentDistance(a,c,d)<=tol||SegmentDistance(b,c,d)<=tol||SegmentDistance(c,a,b)<=tol||SegmentDistance(d,a,b)<=tol)return false;
     double x=Cross(a,b,c),y=Cross(a,b,d),s=Cross(c,d,a),t=Cross(c,d,b);
     if(((x>0&&y<0)||(x<0&&y>0))&&((s>0&&t<0)||(s<0&&t>0)))return false;
    }
   }
   return Math.Abs(area)>tol*tol;
  }
  public static string Classify(double[] p,double[][] v,bool closed,double tol){
   if(!Finite(p)||v==null||v.Length<2||Array.Exists(v,q=>!Finite(q)))return "unknown";
   if(closed&&!Valid(v,tol))return "unknown";
   if(Array.Exists(v,q=>Math.Abs(q[2]-p[2])>tol))return "unknown";
   foreach(var q in v)if(Distance(p,q)<=tol)return "vertex_hit";
   int n=closed?v.Length:v.Length-1;
   for(int i=0;i<n;i++)if(SegmentDistance(p,v[i],v[(i+1)%v.Length])<=tol)return "boundary_hit";
   if(!closed)return "unknown";
   bool inside=false;
   for(int i=0,j=v.Length-1;i<v.Length;j=i++){
    double ax=v[i][0]-p[0],ay=v[i][1]-p[1],bx=v[j][0]-p[0],by=v[j][1]-p[1];
    if((ay>0)!=(by>0) && ax+(bx-ax)*(-ay)/(by-ay)>0)inside=!inside;
   }
   return inside?"interior_hit":"outside";
  }
 }
}
