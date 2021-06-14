import { Component, OnInit } from '@angular/core';
import { Place } from '../place';
import { PlacesService } from '../places.service';
import { Router, ActivatedRoute, ParamMap } from '@angular/router';
@Component({
  selector: 'app-places',
  templateUrl: './places.component.html',
  styleUrls: ['./places.component.css']
})
export class PlacesComponent implements OnInit {

  constructor(
    private router: Router,
    private heroService: PlacesService
    ) { }

  places: Place[] = [
  ];
  ngOnInit(): void {
    this.getPlaces();
  }
  getPlaces(): void {
    this.heroService.getPlaces().subscribe(r => this.places = r);
  }
  clickPlace(id: any) {
    this.heroService.clickPlace(id);
    this.router.navigate(['/place/'+ id]);
    
  }
  
}
