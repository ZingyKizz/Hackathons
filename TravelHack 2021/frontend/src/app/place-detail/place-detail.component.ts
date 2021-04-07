import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute, ParamMap } from '@angular/router';
import { switchMap } from 'rxjs/operators';
import { Place } from '../place';
import { PlacesService } from '../places.service';

@Component({
  selector: 'app-place-detail',
  templateUrl: './place-detail.component.html',
  styleUrls: ['./place-detail.component.css']
})
export class PlaceDetailComponent implements OnInit {
  place: Place = {
    id: 1,
    title: 'string',
    description: 'string',
    image_link: 'a'
  };
id: any;
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private service: PlacesService
  ) { }

  ngOnInit(): void {
    this.id = this.route.snapshot.paramMap.get('id');
    this.service.getPlace(this.id).subscribe(r => this.place = r[0])
  }

}
