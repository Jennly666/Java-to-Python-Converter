public class OuterClass {
    public static void ifElse(int a){
        if(a > 10){
            System.out.println(">10");
        }
        else if(a > 8){
            System.out.println(">8");
        }
        else if(a > 6){
            System.out.println(">6");
        }
        else if(a > 4){
            System.out.println(">4");
        }
        else if(a > 2){
            System.out.println(">2");
        }
        else{
            System.out.println("<=2");
        }
    }
}