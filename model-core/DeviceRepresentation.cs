using System;
using System.Linq;
using System.Collections.Generic;
namespace Mep.DeviceRepresentation {
 public class Relation { public string relationType,status="supported_candidate",physicalConnection="unresolved",portStatus="unresolved"; public double distance; public double[][] intersectionPoints; public string[] endpointTypes; public bool attachmentAllowed; }
 public static class Geometry {
  static double[] Cross(double[] a,double[] b){return new[]{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
  static double[] Unit(double[] v){double n=Math.Sqrt(v.Sum(x=>x*x));if(n<1e-12)throw new ArgumentException("Zero normal");return v.Select(x=>x/n).ToArray();}
  public static double[][] Transform(double[][] points,double[] origin,double[] scale,double rotation,double[] normal,double[] basisOrigin,bool dynamic,bool nested){
   if(dynamic||nested)throw new ArgumentException("Unresolved evaluated representation");
   foreach(var v in new[]{origin,scale,normal,basisOrigin})if(v==null||v.Length!=3||v.Any(x=>double.IsNaN(x)||double.IsInfinity(x)))throw new ArgumentException("Incomplete transform");
   if(scale.Any(x=>x==0)||double.IsNaN(rotation)||double.IsInfinity(rotation))throw new ArgumentException("Invalid transform");
   var n=Unit(normal);var ax=Unit(Cross(Math.Abs(n[0])<1.0/64&&Math.Abs(n[1])<1.0/64?new[]{0.0,1.0,0.0}:new[]{0.0,0.0,1.0},n));var ay=Cross(n,ax);
   return points.Select(p=>{if(p.Length!=3||p.Any(x=>double.IsNaN(x)||double.IsInfinity(x)))throw new ArgumentException("Invalid point");double x=(p[0]-basisOrigin[0])*scale[0],y=(p[1]-basisOrigin[1])*scale[1],z=(p[2]-basisOrigin[2])*scale[2];double u=x*Math.Cos(rotation)-y*Math.Sin(rotation),v=x*Math.Sin(rotation)+y*Math.Cos(rotation);return Enumerable.Range(0,3).Select(i=>origin[i]+ax[i]*u+ay[i]*v+n[i]*z).ToArray();}).ToArray();
  }
  static double Distance(double[] p,double[] a,double[] b){double x=b[0]-a[0],y=b[1]-a[1],q=x*x+y*y;if(q==0)return Math.Sqrt(Math.Pow(p[0]-a[0],2)+Math.Pow(p[1]-a[1],2));double t=Math.Max(0,Math.Min(1,((p[0]-a[0])*x+(p[1]-a[1])*y)/q));return Math.Sqrt(Math.Pow(p[0]-a[0]-t*x,2)+Math.Pow(p[1]-a[1]-t*y,2));}
  static bool Inside(double[] p,double[][] ring){bool yes=false;for(int i=0,j=ring.Length-1;i<ring.Length;j=i++)if((ring[i][1]>p[1])!=(ring[j][1]>p[1])&&p[0]<(ring[j][0]-ring[i][0])*(p[1]-ring[i][1])/(ring[j][1]-ring[i][1])+ring[i][0])yes=!yes;return yes;}
  public static Relation Relate(double[] a,double[] b,double[][] ring,double tolerance,double near){
   if(ring.Length<3||tolerance<=0||near<tolerance)throw new ArgumentException("Invalid boundary policy");
   if(ring.Any(p=>p.Length!=3||Math.Abs(p[2]-ring[0][2])>tolerance))return new Relation{relationType="unresolved",status="unresolved",endpointTypes=new[]{"unresolved","unresolved"},intersectionPoints=new double[0][]};
   var distances=new[]{a,b}.Select(p=>Enumerable.Range(0,ring.Length).Min(i=>Distance(p,ring[i],ring[(i+1)%ring.Length]))).ToArray();
   var types=new[]{a,b}.Select((p,i)=>distances[i]<=tolerance?"endpoint_on_boundary":Inside(p,ring)?"endpoint_inside_representation":distances[i]<=near?"segment_ends_near_boundary":"no_relation").ToArray();
   var hits=new List<double[]>();for(int i=0;i<ring.Length;i++){var c=ring[i];var d=ring[(i+1)%ring.Length];double x=b[0]-a[0],y=b[1]-a[1],u=d[0]-c[0],v=d[1]-c[1],den=x*v-y*u;if(Math.Abs(den)<1e-15)continue;double t=((c[0]-a[0])*v-(c[1]-a[1])*u)/den,s=((c[0]-a[0])*y-(c[1]-a[1])*x)/den;if(t>=0&&t<=1&&s>=0&&s<=1){var p=new[]{a[0]+t*x,a[1]+t*y,a[2]};if(!hits.Any(h=>Math.Abs(h[0]-p[0])<=tolerance&&Math.Abs(h[1]-p[1])<=tolerance))hits.Add(p);}}
   string kind=types.Contains("endpoint_on_boundary")?"endpoint_on_boundary":types.Contains("endpoint_inside_representation")?"endpoint_inside_representation":hits.Count>=2?"crossing_through_representation":hits.Count==1?"segment_crosses_boundary":types.Contains("segment_ends_near_boundary")?"segment_ends_near_boundary":"no_relation";
   if(kind!="no_relation"&&(Math.Abs(a[2]-ring[0][2])>tolerance||Math.Abs(b[2]-ring[0][2])>tolerance))return new Relation{relationType="unresolved",status="unresolved",distance=distances.Min(),endpointTypes=new[]{"unresolved","unresolved"},intersectionPoints=new double[0][]};
   return new Relation{relationType=kind,distance=hits.Count>0?0:distances.Min(),intersectionPoints=hits.ToArray(),endpointTypes=types,attachmentAllowed=types.Any(t=>t=="endpoint_on_boundary"||t=="endpoint_inside_representation"),status=kind=="segment_ends_near_boundary"?"partial":kind=="no_relation"?"not_applicable":"supported_candidate"};
  }
 }
}
