using System;
using System.Collections.Generic;
using System.Linq;

namespace Mep.LocalUnits {
    // Pure local geometry. No report selection, layer rules, fixture data or legacy imports.
    public class InputEdge {
        public string handle;
        public double[][] vertices;
    }
    public class SourceRef {
        public string handle;
        public int segmentIndex = 0;
        public bool reversed;
        public double endpointResidual;
    }
    public class GeometryEdge {
        public string id;
        public double[][] points;
        public string[] sourceHandles;
        public SourceRef[] sourceRefs;
        public string coincidence;
        public double maxEndpointResidual;
        public double maxEndpointSnapResidual;
        public string[] unitIds;
        internal int a, b;
    }
    public class Unit {
        public string id;
        public string contourId;
        public string kind;
        public string closure;
        public string status = "geometric_hypothesis";
        public string[] geometryEdgeIds;
        public string[] sourceHandles;
        public double[][] vertices;
        public string[] interfaceIds = new string[0];
        public double? width;
        public string boundaryNote;
        internal List<int> edges;
        internal List<int> nodes;
    }
    public class Interface {
        public string id;
        public string geometryEdgeId;
        public string[] unitIds;
        public string[] sourceHandles;
        public double[][] points;
        public double width;
        public string basis = "shared boundary of adjacent units; copy count is not a connectivity rule";
    }
    public class Result {
        public GeometryEdge[] geometryEdges;
        public Contour[] contours;
        public Unit[] units;
        public Interface[] interfaces;
        public string[] unassignedEdgeIds;
        public string[] diagnostics;
    }
    public class Contour {
        public string id;
        public string[] geometryEdgeIds;
        public double[][] vertices;
        public string closure;
        public double maxEndpointSnapResidual;
        public string[] sourceHandles;
    }
    internal class Node {
        public double[] p;
        public List<double[]> members = new List<double[]>();
        public List<int> outgoing = new List<int>();
    }
    internal class HalfEdge { public int from, to, edge, twin; }

    public static class Recognizer {
        static double Distance(double[] a, double[] b) {
            double x=a[0]-b[0], y=a[1]-b[1], z=a[2]-b[2];
            return Math.Sqrt(x*x+y*y+z*z);
        }
        static double[] V(double[] a,double[] b) {return new[]{b[0]-a[0],b[1]-a[1],b[2]-a[2]};}
        static double Cross(double[] a,double[] b) {return a[0]*b[1]-a[1]*b[0];}
        static double Dot(double[] a,double[] b) {return a[0]*b[0]+a[1]*b[1];}
        static double Len(double[] v) {return Math.Sqrt(Dot(v,v));}
        static int ComparePoint(double[] a,double[] b) {
            for(int i=0;i<3;i++){int c=a[i].CompareTo(b[i]);if(c!=0)return c;}return 0;
        }
        static bool Parallel(double[] a,double[] b,double angular) {
            return Math.Abs(Cross(a,b))<=angular*Len(a)*Len(b);
        }
        static int AddNode(List<Node> nodes,double[] p,double tol) {
            var hits=nodes.Where(n=>n.members.Any(q=>Distance(p,q)<=tol)).ToList();
            if(hits.Count>1 || (hits.Count==1 && hits[0].members.Any(q=>Distance(p,q)>tol)))
                throw new ArgumentException("Ambiguous endpoint cluster: transitive tolerance merging is not supported.");
            if(hits.Count==1){hits[0].members.Add(p);return nodes.IndexOf(hits[0]);}
            Node added=new Node{p=(double[])p.Clone()};added.members.Add(p);nodes.Add(added);return nodes.Count-1;
        }
        static int From(List<HalfEdge> half,int h){return half[h].from;}
        static Unit MakeUnit(List<Unit> units,List<GeometryEdge> edges,List<Node> nodes,
                             List<int> boundary,List<int> vertexIds,string closure) {
            Unit u=new Unit {id="U"+(units.Count+1), contourId="C"+(units.Count+1), edges=boundary,nodes=vertexIds,
                closure=closure,kind="unknown",geometryEdgeIds=boundary.Select(i=>edges[i].id).ToArray(),
                sourceHandles=boundary.SelectMany(i=>edges[i].sourceHandles).Distinct().OrderBy(h=>h,StringComparer.Ordinal).ToArray(),
                vertices=vertexIds.Select(i=>(double[])nodes[i].p.Clone()).ToArray()};
            units.Add(u);return u;
        }
        static bool Rectangle(Unit u,List<Node> nodes,double angular) {
            var ring=new List<int>(u.nodes);
            bool changed=true;
            while(changed && ring.Count>3){changed=false;
                for(int i=0;i<ring.Count;i++){
                    double[] a=V(nodes[ring[(i+ring.Count-1)%ring.Count]].p,nodes[ring[i]].p);
                    double[] b=V(nodes[ring[i]].p,nodes[ring[(i+1)%ring.Count]].p);
                    if(Parallel(a,b,angular) && Dot(a,b)>0){ring.RemoveAt(i);changed=true;break;}
                }
            }
            if(ring.Count!=4)return false;
            for(int i=0;i<ring.Count;i++){
                var a=V(nodes[ring[i]].p,nodes[ring[(i+1)%ring.Count]].p);
                var b=V(nodes[ring[(i+1)%ring.Count]].p,nodes[ring[(i+2)%ring.Count]].p);
                if(Math.Abs(Dot(a,b))>angular*Len(a)*Len(b))return false;
            }
            return true;
        }
        // Detect unsupported interior intersections and partial overlaps before face traversal.
        static void ValidateEmbedding(List<GeometryEdge> edges,List<Node> nodes,double tol,double angular) {
            for(int i=0;i<edges.Count;i++)for(int j=i+1;j<edges.Count;j++){
                var a=edges[i];var b=edges[j];var p=nodes[a.a].p;var q=nodes[b.a].p;
                var u=V(p,nodes[a.b].p);var v=V(q,nodes[b.b].p);var delta=V(p,q);
                double lu=Len(u),lv=Len(v),cross=Cross(u,v);
                if(Parallel(u,v,angular)){
                    if(Math.Abs(Cross(u,delta))/lu<=tol){
                        double t=Dot(delta,u)/lu,s=t+Dot(v,u)/lu;
                        double overlap=Math.Min(lu,Math.Max(t,s))-Math.Max(0,Math.Min(t,s));
                        if(overlap>tol)throw new ArgumentException("Partial collinear overlap requires segment splitting; not supported in phase 1.");
                    }
                } else {
                    double t=Cross(delta,v)/cross,s=Cross(delta,u)/cross;
                    if(t>=-tol/lu && t<=1+tol/lu && s>=-tol/lv && s<=1+tol/lv){
                        bool shared=a.a==b.a || a.a==b.b || a.b==b.a || a.b==b.b;
                        if(!shared)throw new ArgumentException("Interior crossing or endpoint-on-interior requires explicit topology review.");
                    }
                }
            }
        }
        public static Result Build(InputEdge[] raw,double tol,double angular) {
            if(raw==null || raw.Length==0 || !Finite(tol) || tol<=0 || !Finite(angular) || angular<=0 || angular>=0.1)
                throw new ArgumentException("Nonempty local input and positive finite tolerances are required.");
            if(raw.Select(e=>e.handle).Distinct().Count()!=raw.Length || raw.Any(e=>String.IsNullOrWhiteSpace(e.handle)))
                throw new ArgumentException("Handles must be nonempty and unique within the supplied drawing snapshot.");
            foreach(var e in raw){
                if(e.vertices==null || e.vertices.Length!=2 || e.vertices.Any(p=>p==null || p.Length!=3 || p.Any(x=>!Finite(x))))
                    throw new ArgumentException("Only finite XYZ straight segments are supported.");
                if(Distance(e.vertices[0],e.vertices[1])<=tol)throw new ArgumentException("Degenerate segment.");
            }
            double minZ=raw.SelectMany(e=>e.vertices).Min(p=>p[2]);
            double maxZ=raw.SelectMany(e=>e.vertices).Max(p=>p[2]);
            if(maxZ-minZ>tol)throw new ArgumentException("Local phase 1 input must share one XY plane; elevations are not silently merged.");
            var sorted=raw.OrderBy(e=>e.vertices.OrderBy(p=>p,Comparer<double[]>.Create(ComparePoint)).First(),Comparer<double[]>.Create(ComparePoint))
                          .ThenBy(e=>e.vertices.OrderBy(p=>p,Comparer<double[]>.Create(ComparePoint)).Last(),Comparer<double[]>.Create(ComparePoint)).ToArray();
            var edges=new List<GeometryEdge>();
            foreach(var e in sorted){
                var p=e.vertices[0];var q=e.vertices[1];bool reversed=ComparePoint(p,q)>0;
                if(reversed){var t=p;p=q;q=t;}
                var matches=edges.Where(existing=>(Distance(p,existing.points[0])<=tol && Distance(q,existing.points[1])<=tol)
                    || (Distance(q,existing.points[0])<=tol && Distance(p,existing.points[1])<=tol)).ToList();
                if(matches.Count>1)throw new ArgumentException("Ambiguous whole-segment equivalence.");
                GeometryEdge g;
                if(matches.Count==0){g=new GeometryEdge{id="G"+(edges.Count+1),points=new[]{(double[])p.Clone(),(double[])q.Clone()},sourceHandles=new string[0],sourceRefs=new SourceRef[0],coincidence="single_source"};edges.Add(g);}
                else {
                    g=matches[0];
                    if(Distance(p,g.points[0])>tol || Distance(q,g.points[1])>tol){var swap=p;p=q;q=swap;reversed=!reversed;}
                }
                // A group must be pairwise close, not just close to one representative.
                foreach(var reference in g.sourceRefs){
                    var original=raw.First(x=>x.handle==reference.handle);
                    var a=original.vertices[reference.reversed?1:0];var b=original.vertices[reference.reversed?0:1];
                    if(Distance(a,p)>tol || Distance(b,q)>tol)throw new ArgumentException("Non-pairwise duplicate cluster.");
                }
                double residual=Math.Max(Distance(p,g.points[0]),Distance(q,g.points[1]));
                g.sourceHandles=g.sourceHandles.Concat(new[]{e.handle}).ToArray();
                g.sourceRefs=g.sourceRefs.Concat(new[]{new SourceRef{handle=e.handle,reversed=reversed,endpointResidual=residual}}).ToArray();
                g.maxEndpointResidual=Math.Max(g.maxEndpointResidual,residual);
                if(g.sourceHandles.Length>1)g.coincidence=g.maxEndpointResidual==0?"exact_report_coordinates":"within_tolerance";
            }
            var nodes=new List<Node>();
            foreach(var e in edges){e.a=AddNode(nodes,e.points[0],tol);e.b=AddNode(nodes,e.points[1],tol);if(e.a==e.b)throw new ArgumentException("Tolerance collapsed an edge.");
                e.maxEndpointSnapResidual=Math.Max(Distance(e.points[0],nodes[e.a].p),Distance(e.points[1],nodes[e.b].p));}
            ValidateEmbedding(edges,nodes,tol,angular);
            var half=new List<HalfEdge>();
            for(int i=0;i<edges.Count;i++){
                var e=edges[i];int h=half.Count;
                half.Add(new HalfEdge{from=e.a,to=e.b,edge=i,twin=h+1});half.Add(new HalfEdge{from=e.b,to=e.a,edge=i,twin=h});
                nodes[e.a].outgoing.Add(h);nodes[e.b].outgoing.Add(h+1);
            }
            foreach(var n in nodes)n.outgoing.Sort((x,y)=>{
                var a=V(n.p,nodes[half[x].to].p);var b=V(n.p,nodes[half[y].to].p);
                return Math.Atan2(a[1],a[0]).CompareTo(Math.Atan2(b[1],b[0]));
            });
            var visited=new HashSet<int>();var units=new List<Unit>();var diagnostics=new List<string>();
            for(int start=0;start<half.Count;start++){
                if(visited.Contains(start))continue;
                var walk=new List<int>();int h=start;
                do {
                    if(visited.Contains(h))throw new ArgumentException("Invalid face traversal.");
                    visited.Add(h);walk.Add(h);
                    var outList=nodes[half[h].to].outgoing;int reverse=outList.IndexOf(half[h].twin);
                    h=outList[(reverse+outList.Count-1)%outList.Count];
                }while(h!=start);
                var ring=walk.Select(x=>From(half,x)).ToList();
                var origin=nodes[ring[0]].p;double area2=0;
                for(int i=0;i<ring.Count;i++)area2+=Cross(V(origin,nodes[ring[i]].p),V(origin,nodes[ring[(i+1)%ring.Count]].p));
                if(area2<=tol*tol)continue; // exterior face and zero-area dangling walks
                if(ring.Distinct().Count()!=ring.Count){diagnostics.Add("Non-simple bounded face retained as unresolved; no unit inferred.");continue;}
                var u=MakeUnit(units,edges,nodes,walk.Select(x=>half[x].edge).ToList(),ring,"closed");
                if(Rectangle(u,nodes,angular))u.kind="straight";
                u.boundaryNote="Observed bounded face; all listed boundary segments are present.";
            }
            var used=new HashSet<int>(units.SelectMany(u=>u.edges));
            var proposals=new List<int[]>();
            // A partial straight consists of two free parallel sides attached to a bounded face's transverse edge.
            foreach(var face in units.ToArray())for(int k=0;k<face.edges.Count;k++){
                int edgeId=face.edges[k],a=face.nodes[k],b=face.nodes[(k+1)%face.nodes.Count];
                if(units.Count(u=>u.edges.Contains(edgeId))!=1)continue;
                var atA=Enumerable.Range(0,edges.Count).Where(i=>!used.Contains(i)&&(edges[i].a==a||edges[i].b==a)).ToArray();
                var atB=Enumerable.Range(0,edges.Count).Where(i=>!used.Contains(i)&&(edges[i].a==b||edges[i].b==b)).ToArray();
                foreach(int x in atA)foreach(int y in atB){
                    if(x==y)continue;
                    int farA=edges[x].a==a?edges[x].b:edges[x].a,farB=edges[y].a==b?edges[y].b:edges[y].a;
                    var sideA=V(nodes[a].p,nodes[farA].p);var sideB=V(nodes[b].p,nodes[farB].p);var cap=V(nodes[a].p,nodes[b].p);
                    if(!Parallel(sideA,sideB,angular)||Dot(sideA,sideB)<=0)continue;
                    if(Math.Abs(Dot(cap,sideA))>angular*Len(cap)*Len(sideA))continue;
                    if(Cross(cap,sideA)>=0)continue; // bounded face is to the left; open strip must lie outside it
                    proposals.Add(new[]{edgeId,x,y,farA,a,b,farB});
                }
            }
            foreach(var p in proposals){
                if(proposals.Any(q=>!Object.ReferenceEquals(p,q)&&(q[1]==p[1]||q[2]==p[1]||q[1]==p[2]||q[2]==p[2]))){diagnostics.Add("Competing partial straight hypotheses; no automatic assignment.");continue;}
                var u=MakeUnit(units,edges,nodes,new List<int>{p[1],p[0],p[2]},new List<int>{p[3],p[4],p[5],p[6]},"unknown_far_end");
                u.kind="straight";u.width=Distance(nodes[p[4]].p,nodes[p[5]].p);
                u.boundaryNote="Two observed parallel sides and one interface; no far-end edge invented, continuation unknown.";
            }
            var interfaces=new List<Interface>();
            for(int i=0;i<edges.Count;i++){
                var e=edges[i];var incident=units.Where(u=>u.edges.Contains(i)).ToArray();e.unitIds=incident.Select(u=>u.id).ToArray();
                if(incident.Length==2){
                    interfaces.Add(new Interface{id="I"+(interfaces.Count+1),geometryEdgeId=e.id,unitIds=e.unitIds,sourceHandles=e.sourceHandles,points=e.points,width=Distance(e.points[0],e.points[1])});
                }else if(incident.Length>2)diagnostics.Add("Ambiguous shared edge "+e.id+"; not converted to a multiway connection.");
            }
            foreach(var u in units){
                var ports=interfaces.Where(i=>i.unitIds.Contains(u.id)).ToArray();u.interfaceIds=ports.Select(i=>i.id).ToArray();
                if(u.kind=="straight" && ports.Length>0){
                    if(ports.All(i=>Math.Abs(i.width-ports[0].width)<=tol))u.width=ports[0].width;
                    else {u.width=null;diagnostics.Add("Inconsistent straight interface widths at "+u.id);}
                }
                if(u.kind=="unknown" && ports.Length==2){
                    var a=V(ports[0].points[0],ports[0].points[1]);var b=V(ports[1].points[0],ports[1].points[1]);
                    if(!Parallel(a,b,angular) && Math.Abs(ports[0].width-ports[1].width)<=tol)u.kind="bend";
                }
            }
            var contours=units.Select(u=>new Contour{id=u.contourId,geometryEdgeIds=u.geometryEdgeIds,vertices=u.vertices,
                closure=u.closure,sourceHandles=u.sourceHandles,maxEndpointSnapResidual=u.edges.Max(i=>edges[i].maxEndpointSnapResidual)}).ToArray();
            return new Result{geometryEdges=edges.ToArray(),contours=contours,units=units.ToArray(),interfaces=interfaces.ToArray(),
                unassignedEdgeIds=edges.Where(e=>e.unitIds.Length==0).Select(e=>e.id).ToArray(),diagnostics=diagnostics.Distinct().ToArray()};
        }
        static bool Finite(double x){return !Double.IsNaN(x)&&!Double.IsInfinity(x);}
    }
}
